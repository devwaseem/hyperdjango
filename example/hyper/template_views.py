from __future__ import annotations

from hyper.templates.profile_card.page import ProfileCardTemplate
from hyperdjango.shortcuts import render_template_page


def profile_card(request):
    return render_template_page(
        request,
        ProfileCardTemplate,
        context={
            "title": "Template Package Demo",
            "description": "This card is rendered from hyper/templates without file routing.",
        },
    )
