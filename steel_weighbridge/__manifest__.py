{
    "name": "Steel Weighbridge",
    "version": "19.0.1.0.0",
    "category": "Supply Chain",
    "summary": "Weighbridge tickets, tonnage pricing and multi-currency reporting for steel traders",
    "description": """
Weighbridge tickets for steel trading on Odoo 19:

* gross / tare weighing with net weight in kg and tonnes (editable both ways)
* tonnage pricing in the ticket currency and monthly totals per currency
* draft -> weighed -> done workflow, cancellation by reversal (never by deletion)
* one open weighing per truck, enforced by a partial unique index in PostgreSQL
* sales / purchase isolation with record rules and multi-company rules
* printable weighbridge ticket and an idempotent daily summary job
""",
    "author": "Modar Dwery",
    "website": "https://github.com/modar-m-dwery/odoo-steel-weighbridge",
    "license": "LGPL-3",
    "depends": ["mail"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "data/ir_cron.xml",
        "views/weigh_ticket_views.xml",
        "views/daily_summary_views.xml",
        "views/menus.xml",
        "report/weigh_ticket_report.xml",
    ],
    "demo": [
        "demo/demo.xml",
    ],
    "installable": True,
    "application": True,
}
