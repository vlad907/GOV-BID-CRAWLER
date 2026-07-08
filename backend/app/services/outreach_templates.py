from jinja2 import Template

SUBJECT_TEMPLATE = Template(
    "Bulk / wholesale pricing inquiry - NSN {{ nsn }}{% if title %} ({{ title }}){% endif %}"
)

BODY_TEMPLATE = Template(
    """Hello{% if supplier_name %} {{ supplier_name }} team{% endif %},

We're sourcing the following part for an upcoming government solicitation and would
like to request your best wholesale/bulk pricing:

  NSN: {{ nsn }}
{% if title %}  Description: {{ title }}
{% endif %}{% if qty %}  Quantity needed: {{ qty }}
{% endif %}{% if specs %}
Specs / dimensions:
{% for key, value in specs.items() %}  - {{ key }}: {{ value }}
{% endfor %}{% endif %}
Could you let us know your best unit price at this quantity, minimum order
quantity, and lead time? We have a submission deadline of
{{ close_date or "TBD" }} and would appreciate a quote as soon as possible.

Thank you,
"""
)


def render_outreach_draft(
    supplier_name: str | None,
    nsn: str | None,
    title: str | None,
    qty: int | None,
    specs: dict | None,
    close_date: str | None,
) -> tuple[str, str]:
    ctx = dict(
        supplier_name=supplier_name,
        nsn=nsn or "N/A",
        title=title,
        qty=qty,
        specs=specs or {},
        close_date=close_date,
    )
    subject = SUBJECT_TEMPLATE.render(**ctx)
    body = BODY_TEMPLATE.render(**ctx)
    return subject, body
