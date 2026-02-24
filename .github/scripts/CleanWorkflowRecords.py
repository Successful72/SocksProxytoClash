#!/usr/bin/env python3
"""
清理 GitHub Actions 工作流记录
- 只处理已完成 (completed) 的 runs
- 永远跳过当前正在运行的 run
- 最终仅保留最近 KEEP_COUNT 条
"""

import os
import requests
from datetime import datetime

def clean_workflow_records():
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    workflow_name = os.getenv("WORKFLOW_NAME", "Update Clash Proxies")
    keep_count = int(os.getenv("KEEP_COUNT", 3))
    current_run_id = int(os.getenv("GITHUB_RUN_ID", "0"))

    if not token or not repo:
        print("错误: 缺少 GITHUB_TOKEN 或 GITHUB_REPOSITORY")
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        # 1. 获取 workflow ID
        workflows_url = f"https://api.github.com/repos/{repo}/actions/workflows"
        resp = requests.get(workflows_url, headers=headers)
        resp.raise_for_status()

        workflow_id = None
        for wf in resp.json().get("workflows", []):
            if wf.get("name") == workflow_name:
                workflow_id = wf["id"]
                break

        if not workflow_id:
            print(f"错误: 找不到工作流 {workflow_name}")
            return False

        # 2. 拉取所有 workflow runs（分页）
        all_runs = []
        page = 1
        per_page = 100

        while True:
            runs_url = (
                f"https://api.github.com/repos/{repo}"
                f"/actions/workflows/{workflow_id}/runs"
                f"?per_page={per_page}&page={page}"
            )
            resp = requests.get(runs_url, headers=headers)
            resp.raise_for_status()

            runs = resp.json().get("workflow_runs", [])
            if not runs:
                break

            all_runs.extend(runs)
            page += 1

        print(f"共获取到 {len(all_runs)} 条运行记录")

        # 3. 排序（按时间倒序）
        all_runs.sort(key=lambda r: r["created_at"], reverse=True)

        # 4. 过滤：只保留 completed 且不是当前 run
        deletable_runs = []
        kept = 0

        for run in all_runs:
            if run["id"] == current_run_id:
                continue

            if run["status"] != "completed":
                continue

            if kept < keep_count:
                kept += 1
                continue

            deletable_runs.append(run)

        print(f"将保留最近 {keep_count} 条已完成记录")
        print(f"准备删除 {len(deletable_runs)} 条旧记录")

        # 5. 删除
        for i, run in enumerate(deletable_runs, 1):
            run_id = run["id"]
            created_at = datetime.fromisoformat(
                run["created_at"].replace("Z", "+00:00")
            )

            print(
                f"[{i}/{len(deletable_runs)}] "
                f"删除 run {run_id}（{created_at}）"
            )

            del_url = (
                f"https://api.github.com/repos/{repo}"
                f"/actions/runs/{run_id}"
            )
            del_resp = requests.delete(del_url, headers=headers)

            if del_resp.status_code == 204:
                print("  ✓ 删除成功")
            else:
                print(
                    f"  ✗ 删除失败: {del_resp.status_code} "
                    f"{del_resp.text}"
                )

        print("清理完成")
        return True

    except Exception as e:
        print(f"发生错误: {e}")
        return False


if __name__ == "__main__":
    if not clean_workflow_records():
        exit(1)
