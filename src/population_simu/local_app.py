"""无额外依赖的本地应用入口。

启动后会同时提供 ``docs/`` 网页和完整 Python 家庭引擎 API：

    PYTHONPATH=src python3 -m population_simu.local_app

API 只允许读取仓库 ``scenarios/`` 下的情景文件，适合本地探索，不是生产服务。
"""

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .family_config import FamilyScenario
from .family_world import FamilyWorld


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = PROJECT_ROOT / "docs"
SCENARIO_ROOT = PROJECT_ROOT / "scenarios"


def available_scenarios() -> list[str]:
    return sorted(path.name for path in SCENARIO_ROOT.glob("*.json"))


def run_scenario(
    filename: str,
    end_year: int | None = None,
    years: int | None = None,
    seed: int | None = None,
) -> dict[str, object]:
    if Path(filename).name != filename or not filename.endswith(".json"):
        raise ValueError("scenario 必须是 scenarios/ 下的 JSON 文件名")
    path = SCENARIO_ROOT / filename
    if not path.is_file():
        raise FileNotFoundError(filename)
    data = json.loads(path.read_text(encoding="utf-8"))
    if seed is not None:
        data.setdefault("simulation", {})["random_seed"] = seed
    scenario = FamilyScenario.from_dict(data)
    if years is not None:
        if years < 0:
            raise ValueError("years 不能为负数")
        target = scenario.simulation.start_year + years
    else:
        target = end_year if end_year is not None else scenario.simulation.end_year
    if target < scenario.simulation.start_year or target > scenario.simulation.end_year:
        raise ValueError("end_year 必须位于情景的 start_year 和 end_year 之间")
    world = FamilyWorld(scenario)
    history = world.run(target)
    return {
        "scenario": filename,
        "snapshot": world.snapshot(),
        "history": [row.flat_dict() for row in history],
    }


class LocalAppHandler(SimpleHTTPRequestHandler):
    """为 docs 静态文件增加三个只读 JSON 接口。"""

    server_version = "PopulationSimuLocal/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS_ROOT), **kwargs)

    def _json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._json({"ok": True, "engine": "python", "scenarios": available_scenarios()})
            return
        if parsed.path == "/api/scenarios":
            self._json({"scenarios": available_scenarios()})
            return
        if parsed.path == "/api/run":
            params = parse_qs(parsed.query)
            filename = params.get("scenario", ["family_major_countries.json"])[0]
            end_year = int(params["end_year"][0]) if params.get("end_year") else None
            years = int(params["years"][0]) if params.get("years") else None
            seed = int(params["seed"][0]) if params.get("seed") else None
            try:
                self._json(run_scenario(filename, end_year=end_year, years=years, seed=seed))
            except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
                self._json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        super().do_GET()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="启动 Population Simu 本地应用")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址，默认仅本机")
    parser.add_argument("--port", type=int, default=8000, help="监听端口")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not DOCS_ROOT.is_dir():
        raise SystemExit(f"找不到网页目录：{DOCS_ROOT}")
    server = ThreadingHTTPServer((args.host, args.port), LocalAppHandler)
    print(f"Population Simu local app: http://{args.host}:{args.port}/")
    print(f"Python API: http://{args.host}:{args.port}/api/health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止本地应用")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
