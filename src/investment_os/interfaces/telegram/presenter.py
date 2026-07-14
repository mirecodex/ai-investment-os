"""Rendering for Telegram (HTML parse mode, Bahasa Indonesia).

Output order follows the explainability template (docs/fase-2, doc 09 and
fase-4, doc 03): keputusan + confidence → alasan → rule → risiko → evidence →
disclaimer. Wording stays hedged by construction — no template here may state
certainty or promised returns (rule R4 lives in this layer).
"""

from __future__ import annotations

import html

from investment_os.core.explain import AnalysisReport
from investment_os.domain import MarketBrief, Stance, Verdict

DISCLAIMER = "<i>Riset & edukasi, bukan nasihat investasi. Keputusan tetap tanggung jawab Anda.</i>"

_VERDICT_LABEL = {
    Verdict.BUY: "BUY",
    Verdict.HOLD: "HOLD",
    Verdict.SELL: "SELL",
    Verdict.ABSTAIN: "ABSTAIN (bukti kurang)",
}

_SENTIMENT_LABEL = {
    Stance.POSITIVE: "Bullish",
    Stance.NEUTRAL: "Netral",
    Stance.NEGATIVE: "Bearish",
}


def _esc(text: str) -> str:
    return html.escape(text, quote=False)


def render_report(report: AnalysisReport) -> str:
    decision = report.decision
    lines = [
        f"<b>{_esc(report.ticker)}</b> · {_esc(report.company)} ({_esc(report.sector)})",
        f"Keputusan: <b>{_VERDICT_LABEL[decision.verdict]}</b> · "
        f"Confidence {decision.confidence * 100:.0f}% ({decision.confidence_band})",
        "",
        f"<b>Alasan utama:</b> {_esc(report.headline)}",
    ]

    if report.bull_case.points:
        lines.append("")
        lines.append("<b>Argumen bull:</b>")
        lines.extend(f"• {_esc(p.claim)}" for p in report.bull_case.points[:3])
    if report.bear_case.points:
        lines.append("")
        lines.append("<b>Argumen bear:</b>")
        lines.extend(f"• {_esc(p.claim)}" for p in report.bear_case.points[:3])

    rule_notes = [t for t in decision.triggered_rules if t.effect != "FLAG_REVIEW"]
    if rule_notes:
        lines.append("")
        lines.append("<b>Rule aktif:</b>")
        lines.extend(f"• [{_esc(t.rule_id)}] {_esc(t.reason)}" for t in rule_notes)

    if report.risks:
        lines.append("")
        lines.append("<b>Risiko & catatan:</b>")
        lines.extend(f"• {_esc(r)}" for r in report.risks[:4])

    if report.evidence:
        lines.append("")
        lines.append("<b>Evidence:</b>")
        lines.extend(f"• {_esc(ref.summary)} — {_esc(ref.source)}" for ref in report.evidence[:5])

    if decision.requires_review:
        lines.append("")
        lines.append("⚠️ Confidence rendah — perlakukan sebagai bahan riset awal.")

    lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def render_brief(brief: MarketBrief) -> str:
    macro = brief.macro
    lines = [
        f"<b>Market Brief · {brief.date.isoformat()}</b>",
        f"Sentimen: <b>{_SENTIMENT_LABEL[brief.sentiment]}</b> · "
        f"Confidence {brief.confidence * 100:.0f}%",
        "",
        *(f"• {_esc(h)}" for h in brief.highlights),
        "",
        f"Makro: BI Rate {macro.bi_rate_pct:.2f}% · USD/IDR {macro.usd_idr:,.0f}",
    ]
    if macro.commodities:
        commodities = " · ".join(f"{k} {v:+.1f}%" for k, v in macro.commodities.items())
        lines.append(f"Komoditas: {_esc(commodities)}")
    lines.append("")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def render_help() -> str:
    return "\n".join(
        [
            "<b>Perintah:</b>",
            "/brief — Market Brief hari ini",
            "/analyze &lt;TICKER&gt; — analisis emiten (mis. /analyze BBCA)",
            "/watchlist — lihat watchlist",
            "/add &lt;TICKER&gt; · /remove &lt;TICKER&gt; — kelola watchlist",
            "/subscribe · /unsubscribe — Market Brief harian otomatis",
            "/help — bantuan",
        ]
    )


def render_start() -> str:
    return "\n".join(
        [
            "Halo! Saya asisten riset saham IDX.",
            "Saya merangkum data pasar, berita, dan fundamental menjadi analisis "
            "ber-alasan — lengkap dengan evidence dan tingkat keyakinan.",
            "",
            render_help(),
            "",
            DISCLAIMER,
        ]
    )
