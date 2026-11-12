# 运行日志模板

项目完整结束后，在目标项目根目录创建：

```text
quality-loop/<YYYYMMDD-HHMMSS>/
|-- report.md
`-- state.json
```

执行过程中可以保留最小运行状态；最终材料一次性发布。不要复制整个项目，只保存评分、证据、修改摘要和必要的小型快照或差异。

## report.md

```markdown
# 提示词符合度闭环报告

## 结果摘要

- 运行编号：{{run_id}}
- 最终状态：{{passed_or_failed}}
- AI 参考满意度：{{score}}
- 用户阈值：{{threshold}}
- 使用轮数：{{current_round}} / {{max_rounds}}
- 审查模式：{{independent_reviewer_or_single_reviewer}}
- 最终交付物：{{deliverable_paths}}

## 原始提示词

{{original_prompt_or_redacted_snapshot}}

## 提示词消化与假设

- 项目目标：
- 交付成果：
- 用户满意标准：
- 优先级与禁止事项：
- 必要假设：

## 有效项目规格

| 需求编号 | 要求 | 优先级 | 权重 | 来源 |
|---|---|---:|---:|---|
| R1 | {{requirement_text}} | P0 | 3 | user-original |

## 验收证据

| 需求编号 | 状态 | 证据 | 审查者 |
|---|---|---|---|
| R1 | {{met_partial_unmet_unverifiable}} | {{evidence}} | {{reviewer}} |

## 阶段时间线

1. {{stage_name}}：{{action_and_outcome}}

## 每轮结果

| 轮次 | 修改目标 | 主要修改 | 满意度 | P0 状态 | 剩余问题 |
|---:|---|---|---:|---|---|
| 1 | {{revision_goal}} | {{changes}} | {{score}} | {{p0_status}} | {{remaining_gaps}} |

## 最终成果

- {{artifact_path_and_purpose}}

## 未解决项

- {{unresolved_item_or_none}}

## 停止原因

{{threshold_reached_or_round_limit_or_blocker}}

## 最终结论

{{passed_or_failed_without_overstating}}
```

## state.json

`state.json` 至少包含以下评分字段，其他审计字段可以附加：

```json
{
  "run_id": "20261112-153000",
  "threshold": 0.8,
  "max_rounds": 3,
  "current_round": 1,
  "review_mode": "independent",
  "requirements": [
    {
      "id": "R1",
      "text": "用户要求",
      "priority": "P0",
      "source": "user-original",
      "status": "met",
      "evidence": "可检查的证据"
    }
  ],
  "score_history": [0.76, 0.86],
  "final_decision": "pass"
}
```

最终写入前检查：

- 所有需求都有状态和证据。
- `P0` 否决没有被平均数掩盖。
- 每轮均有满意度与修改摘要。
- 日志未包含密码、令牌、私钥或其他敏感凭据。
