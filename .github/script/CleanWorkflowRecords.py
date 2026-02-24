#!/usr/bin/env python3
"""
清理 GitHub Actions 工作流记录
只保留最新的几条记录，具体数字在Workflow文件中可指定
"""

import os
import requests
from datetime import datetime

def clean_workflow_records():
    # 从环境变量获取配置
    token = os.getenv('GITHUB_TOKEN')
    repo = os.getenv('GITHUB_REPOSITORY')
    workflow_name = os.getenv('WORKFLOW_NAME', 'Update Clash Proxies')
    keep_count = int(os.getenv('KEEP_COUNT', 3))
    
    if not token or not repo:
        print("错误: 缺少必要的环境变量 GITHUB_TOKEN 或 GITHUB_REPOSITORY")
        return False
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        # 1. 获取工作流 ID
        print(f"正在查找工作流: {workflow_name}")
        workflows_url = f"https://api.github.com/repos/{repo}/actions/workflows"
        workflows_response = requests.get(workflows_url, headers=headers)
        workflows_response.raise_for_status()
        
        workflow_id = None
        for workflow in workflows_response.json()['workflows']:
            if workflow['name'] == workflow_name:
                workflow_id = workflow['id']
                print(f"找到工作流 ID: {workflow_id}")
                break
        
        if not workflow_id:
            print(f"错误: 找不到名为 '{workflow_name}' 的工作流")
            return False
        
        # 2. 获取工作流运行记录
        runs_url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/runs"
        runs_response = requests.get(runs_url, headers=headers)
        runs_response.raise_for_status()
        
        runs = runs_response.json()['workflow_runs']
        print(f"找到 {len(runs)} 条运行记录")
        
        # 3. 删除多余的记录（跳过最新的 keep_count 条）
        runs_to_delete = runs[keep_count:]  # 从索引 keep_count 开始到末尾的都是要删除的
        print(f"将保留最新的 {keep_count} 条记录，删除 {len(runs_to_delete)} 条旧记录")
        
        for i, run in enumerate(runs_to_delete, 1):
            run_id = run['id']
            created_at = datetime.fromisoformat(run['created_at'].replace('Z', '+00:00'))
            print(f"正在删除记录 {i}/{len(runs_to_delete)}: ID {run_id} (创建于 {created_at})")
            
            delete_url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}"
            delete_response = requests.delete(delete_url, headers=headers)
            
            if delete_response.status_code == 204:
                print(f"  ✓ 删除成功")
            else:
                print(f"  ✗ 删除失败: {delete_response.status_code}")
        
        print("清理完成！")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"API 请求错误: {e}")
        return False
    except Exception as e:
        print(f"未知错误: {e}")
        return False

if __name__ == "__main__":
    success = clean_workflow_records()
    if not success:
        exit(1)
