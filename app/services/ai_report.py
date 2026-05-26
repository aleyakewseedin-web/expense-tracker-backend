from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

def generate_financial_narrative(summary: dict, month: str) -> str:
    if summary["total_expenses_count"] == 0:
        return "No expenses recorded for this period."

    categories_text = ""
    for cat in summary["categories"]:
        budget_info = ""
        if cat["budget_usd"]:
            status = "OVER BUDGET" if cat["over_budget"] else "under budget"
            budget_info = f" (budget: ${cat['budget_usd']:.2f}, {status}"
            if cat["over_budget"]:
                budget_info += f", over by ${cat['over_by_usd']:.2f}"
            budget_info += ")"
        categories_text += f"- {cat['category_name']}: ${cat['spent_usd']:.2f}{budget_info}\n"

    has_prev = summary["previous_month_total_usd"] > 0
    prev_context = (
        f"Previous month total: ${summary['previous_month_total_usd']:.2f} "
        f"(change: {summary['month_over_month_change_pct']}%)"
        if has_prev else
        "Previous month: No data available (this may be the first month of tracking)"
    )

    prompt = f"""You are a personal finance advisor analyzing a user's monthly expenses for {month}.

Total spent this month: ${summary['total_spent_usd']:.2f}
{prev_context}

Spending by category:
{categories_text}

Write a concise, friendly financial insight covering exactly these 4 points:
1. The category with highest spending or biggest overspend — be specific with numbers
2. A positive observation about staying under budget (only if budget data exists, otherwise skip)
3. Comparison to previous month — if no previous month data exists, say this is the first tracked month and focus on current patterns instead
4. One specific actionable recommendation with concrete numbers

Rules:
- Never mention "last month" if previous month total is $0 or unavailable
- Be specific with dollar amounts
- Keep it encouraging
- Write as one flowing paragraph, maximum 120 words
- Do not use numbered lists"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful personal finance advisor. Be concise, specific, and encouraging. Never fabricate data."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=300,
        temperature=0.7
    )

    return response.choices[0].message.content.strip()