#!/usr/bin/env python3
"""
Token使用量监控工具 / Token Usage Monitoring Tool
实时查看和分析Claude API token消耗情况 / Real-time view and analysis of Claude API token consumption
"""

import json
import csv
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# 可选依赖，如果没有安装pandas就手动处理 / Optional dependencies, manual processing if pandas not installed
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("⚠️  pandas未安装，使用基础功能 / pandas not installed, using basic functionality")

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

class TokenMonitor:
    """Token监控分析器 / Token monitoring analyzer"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.token_log_file = self.log_dir / "token_usage.log"
        self.token_csv_file = self.log_dir / "token_usage.csv"
    
    def parse_log_file(self) -> List[Dict[str, Any]]:
        """解析token使用日志文件 / Parse token usage log file"""
        usage_data = []
        
        if not self.token_log_file.exists():
            print(f"⚠️  Token日志文件不存在: {self.token_log_file}")
            return usage_data
        
        with open(self.token_log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if 'TOKEN_USAGE' in line:
                    try:
                        # 提取JSON部分 / Extract JSON part
                        json_start = line.find('{')
                        if json_start != -1:
                            json_str = line[json_start:].strip()
                            data = json.loads(json_str)
                            usage_data.append(data)
                    except json.JSONDecodeError:
                        continue
        
        return usage_data
    
    def parse_csv_file(self):
        """解析CSV文件 / Parse CSV file"""
        if not HAS_PANDAS:
            print("⚠️  需要pandas支持CSV分析功能 / pandas required for CSV analysis")
            return None
            
        if not self.token_csv_file.exists():
            print(f"⚠️  Token CSV文件不存在: {self.token_csv_file}")
            return pd.DataFrame() if HAS_PANDAS else None
        
        try:
            df = pd.read_csv(self.token_csv_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        except Exception as e:
            print(f"❌ 解析CSV失败: {e}")
            return pd.DataFrame() if HAS_PANDAS else None
    
    def show_current_status(self):
        """显示当前状态 / Show current status"""
        print("🔍 Token使用量实时监控 / Token Usage Real-time Monitoring")
        print("=" * 60)
        
        usage_data = self.parse_log_file()
        
        if not usage_data:
            print("📝 暂无token使用记录 / No token usage records yet")
            return
        
        # 今日统计 / Today's statistics
        today = datetime.now().strftime("%Y-%m-%d")
        today_data = [d for d in usage_data if d.get('timestamp', '').startswith(today)]
        
        if today_data:
            total_input = sum(d.get('input_tokens', 0) for d in today_data)
            total_output = sum(d.get('output_tokens', 0) for d in today_data)
            total_cost = sum(d.get('cost_usd', 0) for d in today_data)
            total_requests = len(today_data)
            
            print(f"📊 今日统计 ({today}) / Today's Statistics:")
            print(f"  • 总请求数 / Total Requests: {total_requests}")
            print(f"  • 输入Tokens / Input Tokens: {total_input:,}")
            print(f"  • 输出Tokens / Output Tokens: {total_output:,}")
            print(f"  • 总Tokens / Total Tokens: {total_input + total_output:,}")
            print(f"  • 总成本 / Total Cost: ${total_cost:.4f}")
            print(f"  • 平均每次请求成本 / Avg Cost per Request: ${total_cost/total_requests:.4f}")
        
        # 最近10次使用 / Recent 10 usages
        print(f"\n📋 最近使用记录 / Recent Usage Records:")
        recent_data = usage_data[-10:]
        
        print(f"{'时间':<20} {'会话ID':<12} {'输入':<8} {'输出':<8} {'成本':<10} {'任务类型':<15}")
        print("-" * 80)
        
        for data in recent_data:
            timestamp = data.get('timestamp', '')[:19].replace('T', ' ')
            session_id = data.get('session_id', 'unknown')[:10]
            input_tokens = data.get('input_tokens', 0)
            output_tokens = data.get('output_tokens', 0)
            cost = data.get('cost_usd', 0)
            task_type = data.get('task_type', 'unknown')[:12]
            
            print(f"{timestamp:<20} {session_id:<12} {input_tokens:<8} {output_tokens:<8} ${cost:<9.4f} {task_type:<15}")
    
    def show_daily_summary(self, days: int = 7):
        """显示每日汇总 / Show daily summary"""
        print(f"\n📈 近{days}天使用汇总 / {days}-Day Usage Summary")
        print("=" * 60)
        
        if not HAS_PANDAS:
            print("⚠️  需要pandas支持每日汇总功能 / pandas required for daily summary")
            return
            
        df = self.parse_csv_file()
        if df is None or df.empty:
            print("📝 暂无数据 / No data available")
            return
        
        # 按日期分组 / Group by date
        df['date'] = df['timestamp'].dt.date
        daily_stats = df.groupby('date').agg({
            'input_tokens': 'sum',
            'output_tokens': 'sum',
            'total_tokens': 'sum',
            'cost_usd': 'sum',
            'session_id': 'count'
        }).rename(columns={'session_id': 'requests'})
        
        # 只显示最近几天 / Show only recent days
        recent_stats = daily_stats.tail(days)
        
        print(f"{'日期':<12} {'请求数':<8} {'总Tokens':<10} {'总成本':<10} {'平均/请求':<12}")
        print("-" * 60)
        
        for date, row in recent_stats.iterrows():
            avg_cost = row['cost_usd'] / row['requests'] if row['requests'] > 0 else 0
            print(f"{date:<12} {row['requests']:<8} {row['total_tokens']:<10,} ${row['cost_usd']:<9.3f} ${avg_cost:<11.4f}")
        
        # 总计 / Total
        total_cost = recent_stats['cost_usd'].sum()
        total_requests = recent_stats['requests'].sum()
        total_tokens = recent_stats['total_tokens'].sum()
        
        print("-" * 60)
        print(f"{'总计':<12} {total_requests:<8} {total_tokens:<10,} ${total_cost:<9.3f} 平均: ${total_cost/total_requests:.4f}")
    
    def show_model_breakdown(self):
        """显示模型使用分解 / Show model usage breakdown"""
        print(f"\n🤖 模型使用分解 / Model Usage Breakdown")
        print("=" * 50)
        
        if not HAS_PANDAS:
            print("⚠️  需要pandas支持模型分解功能 / pandas required for model breakdown")
            return
            
        df = self.parse_csv_file()
        if df is None or df.empty:
            print("📝 暂无数据 / No data available")
            return
        
        model_stats = df.groupby('model').agg({
            'input_tokens': 'sum',
            'output_tokens': 'sum',
            'total_tokens': 'sum',
            'cost_usd': 'sum',
            'session_id': 'count'
        }).rename(columns={'session_id': 'requests'})
        
        print(f"{'模型':<25} {'请求数':<8} {'总Tokens':<12} {'总成本':<10}")
        print("-" * 60)
        
        for model, row in model_stats.iterrows():
            print(f"{model:<25} {row['requests']:<8} {row['total_tokens']:<12,} ${row['cost_usd']:<9.3f}")
    
    def show_task_breakdown(self):
        """显示任务类型分解 / Show task type breakdown"""
        print(f"\n📋 任务类型分解 / Task Type Breakdown")
        print("=" * 50)
        
        if not HAS_PANDAS:
            print("⚠️  需要pandas支持任务分解功能 / pandas required for task breakdown")
            return
            
        df = self.parse_csv_file()
        if df is None or df.empty:
            print("📝 暂无数据 / No data available")
            return
        
        task_stats = df.groupby('task_type').agg({
            'input_tokens': 'sum',
            'output_tokens': 'sum',
            'total_tokens': 'sum',
            'cost_usd': 'sum',
            'session_id': 'count'
        }).rename(columns={'session_id': 'requests'})
        
        print(f"{'任务类型':<20} {'请求数':<8} {'总Tokens':<12} {'总成本':<10} {'平均成本':<10}")
        print("-" * 70)
        
        for task_type, row in task_stats.iterrows():
            avg_cost = row['cost_usd'] / row['requests'] if row['requests'] > 0 else 0
            print(f"{task_type:<20} {row['requests']:<8} {row['total_tokens']:<12,} ${row['cost_usd']:<9.3f} ${avg_cost:<9.4f}")
    
    def check_budget_status(self, daily_budget: float = 5.0):
        """检查预算状态 / Check budget status"""
        print(f"\n💰 预算状态检查 / Budget Status Check")
        print("=" * 50)
        
        if not HAS_PANDAS:
            print("⚠️  需要pandas支持预算检查功能 / pandas required for budget check")
            return
            
        df = self.parse_csv_file()
        if df is None or df.empty:
            print("📝 暂无数据 / No data available")
            return
        
        # 今日支出 / Today's spending
        today = datetime.now().date()
        today_data = df[df['timestamp'].dt.date == today]
        today_cost = today_data['cost_usd'].sum()
        
        # 预算分析 / Budget analysis
        remaining = daily_budget - today_cost
        percentage = (today_cost / daily_budget) * 100
        
        # 状态判断 / Status determination
        if remaining <= 0:
            status = "🚨 已超支 / EXCEEDED"
            color = "❌"
        elif remaining < daily_budget * 0.2:
            status = "⚠️  临界 / CRITICAL"
            color = "🟠"
        elif remaining < daily_budget * 0.5:
            status = "⚠️  警告 / WARNING"
            color = "🟡"
        else:
            status = "✅ 安全 / SAFE"
            color = "🟢"
        
        print(f"  • 每日预算 / Daily Budget: ${daily_budget:.2f}")
        print(f"  • 今日已用 / Today Used: ${today_cost:.4f}")
        print(f"  • 剩余预算 / Remaining: ${remaining:.4f}")
        print(f"  • 使用比例 / Usage %: {percentage:.1f}%")
        print(f"  • 状态 / Status: {color} {status}")
        
        # 预测分析 / Prediction analysis
        if today_data.shape[0] > 0:
            current_hour = datetime.now().hour
            if current_hour > 0:
                hourly_rate = today_cost / current_hour
                predicted_daily = hourly_rate * 24
                print(f"  • 预测日消费 / Predicted Daily: ${predicted_daily:.4f}")
    
    def export_report(self, filename: str = None):
        """导出报告 / Export report"""
        if not filename:
            filename = f"token_usage_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # 重定向输出到文件 / Redirect output to file
        import sys
        original_stdout = sys.stdout
        
        with open(filename, 'w', encoding='utf-8') as f:
            sys.stdout = f
            
            print(f"JobCatcher Token使用量报告 / Token Usage Report")
            print(f"生成时间 / Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)
            
            self.show_current_status()
            self.show_daily_summary()
            self.show_model_breakdown()
            self.show_task_breakdown()
            self.check_budget_status()
        
        sys.stdout = original_stdout
        print(f"📄 报告已导出: {filename}")

def main():
    """主函数 / Main function"""
    parser = argparse.ArgumentParser(description="JobCatcher Token使用量监控工具")
    parser.add_argument("--status", action="store_true", help="显示当前状态")
    parser.add_argument("--daily", type=int, default=7, help="显示每日汇总(天数)")
    parser.add_argument("--models", action="store_true", help="显示模型分解")
    parser.add_argument("--tasks", action="store_true", help="显示任务分解")
    parser.add_argument("--budget", type=float, default=5.0, help="检查预算状态")
    parser.add_argument("--export", type=str, nargs='?', const='auto', help="导出报告")
    parser.add_argument("--all", action="store_true", help="显示所有信息")
    
    args = parser.parse_args()
    
    monitor = TokenMonitor()
    
    if args.all or not any([args.status, args.models, args.tasks, args.export]):
        # 默认显示所有信息 / Default show all info
        monitor.show_current_status()
        monitor.show_daily_summary(args.daily)
        monitor.show_model_breakdown()
        monitor.show_task_breakdown()
        monitor.check_budget_status(args.budget)
    else:
        if args.status:
            monitor.show_current_status()
        
        if args.daily:
            monitor.show_daily_summary(args.daily)
        
        if args.models:
            monitor.show_model_breakdown()
        
        if args.tasks:
            monitor.show_task_breakdown()
        
        if args.budget:
            monitor.check_budget_status(args.budget)
    
    if args.export:
        filename = args.export if args.export != 'auto' else None
        monitor.export_report(filename)

if __name__ == "__main__":
    main() 