import json

def generate_report():
    report = "# SageDLP Code Audit Report\n\n"

    # 1. Security Issues (Bandit)
    with open('bandit_report.json') as f:
        bandit_data = json.load(f)

    report += "## 1. Security Analysis (Bandit)\n\n"
    high_issues = [i for i in bandit_data['results'] if i['issue_severity'] == 'HIGH']
    medium_issues = [i for i in bandit_data['results'] if i['issue_severity'] == 'MEDIUM']
    low_issues = [i for i in bandit_data['results'] if i['issue_severity'] == 'LOW']

    report += f"- **High Severity:** {len(high_issues)}\n"
    report += f"- **Medium Severity:** {len(medium_issues)}\n"
    report += f"- **Low Severity:** {len(low_issues)}\n\n"

    if high_issues:
        report += "### High Severity Issues:\n"
        for i in high_issues:
            report += f"- **{i['test_id']}**: {i['issue_text']}\n  - Location: `{i['filename']}:{i['line_number']}`\n"
        report += "\n"

    if medium_issues:
        report += "### Medium Severity Issues:\n"
        for i in medium_issues:
            report += f"- **{i['test_id']}**: {i['issue_text']}\n  - Location: `{i['filename']}:{i['line_number']}`\n"
        report += "\n"

    # 2. Code Quality Issues (Pylint)
    with open('pylint_report.json') as f:
        pylint_data = json.load(f)

    errors = [i for i in pylint_data if i['type'] == 'error']
    warnings = [i for i in pylint_data if i['type'] == 'warning']
    conventions = [i for i in pylint_data if i['type'] == 'convention']
    refactors = [i for i in pylint_data if i['type'] == 'refactor']

    report += "## 2. Code Quality (Pylint)\n\n"
    report += f"- **Errors:** {len(errors)}\n"
    report += f"- **Warnings:** {len(warnings)}\n"
    report += f"- **Refactor:** {len(refactors)}\n"
    report += f"- **Convention:** {len(conventions)}\n\n"

    if errors:
        report += "### Top Errors:\n"
        error_counts = {}
        for e in errors:
            error_counts[e['message-id']] = error_counts.get(e['message-id'], 0) + 1
        for msg_id, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
            msg = next(e['message'] for e in errors if e['message-id'] == msg_id)
            report += f"- **{msg_id}**: {msg} ({count} occurrences)\n"
        report += "\n"

    if warnings:
        report += "### Top Warnings:\n"
        warning_counts = {}
        for w in warnings:
            warning_counts[w['message-id']] = warning_counts.get(w['message-id'], 0) + 1
        for msg_id, count in sorted(warning_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            msg = next(w['message'] for w in warnings if w['message-id'] == msg_id)
            report += f"- **{msg_id}**: {msg} ({count} occurrences)\n"
        report += "\n"

    # 3. Code Complexity (Radon)
    report += "## 3. Code Complexity (Radon)\n\n"
    try:
        with open('radon_cc.txt') as f:
            lines = f.readlines()
            high_complexity = [line for line in lines if " - D" in line or " - E" in line or " - F" in line]

            if high_complexity:
                report += "### High Complexity Blocks (Score D, E, F):\n"
                for line in high_complexity:
                    report += f"- {line.strip()}\n"
    except Exception as e:
        report += f"Error reading radon output: {e}\n"

    return report

with open('audit_report.md', 'w') as f:
    f.write(generate_report())
