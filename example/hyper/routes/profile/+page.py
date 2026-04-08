from __future__ import annotations

from django import forms
from hyper.layouts.base import BaseLayout

from hyperdjango.actions import action


class ProfileForm(forms.Form):
    email = forms.EmailField()
    name = forms.CharField(max_length=255)


class PageView(BaseLayout):
    def get(self, request, **params):
        initial = request.session.get("profile", {"email": "", "name": ""})
        form = ProfileForm(initial=initial)
        return {"form": form, "saved": False, "saved_name": ""}

    def post(self, request, **params):
        action_name = str(request.POST.get("_action", "")).strip()
        if action_name == "save_profile":
            form, saved_name, is_valid = self._validate_and_save(request)
            return {"form": form, "saved": is_valid, "saved_name": saved_name}
        return self.get(request, **params)

    @action
    def save_profile(self, request, **params):
        form, saved_name, is_valid = self._validate_and_save(request)
        if not is_valid:
            return self.action_response(
                html=self.render(
                    request=request,
                    relative_template_name="partials/form.html",
                    context_updates={"form": form},
                ),
                target="#profile-panel",
            )

        return self.action_response(
            html=self.render(
                request=request,
                relative_template_name="partials/success.html",
                context_updates={"saved_name": saved_name},
            ),
            target="#profile-panel",
            swap="inner",
            toast={"type": "success", "title": "Saved", "message": "Profile saved."},
        )

    def _validate_and_save(self, request):
        form = ProfileForm(request.POST)
        if form.is_valid():
            data = {
                "email": form.cleaned_data["email"],
                "name": form.cleaned_data["name"],
            }
            request.session["profile"] = data
            return ProfileForm(initial=data), data["name"], True
        return form, "", False
