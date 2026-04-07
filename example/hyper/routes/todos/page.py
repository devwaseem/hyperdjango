from __future__ import annotations

from uuid import uuid4

from hyper.layouts.base import BaseLayout

from hyperdjango.actions import action


class TodosPage(BaseLayout):
    def get(self, request, **params):
        todos = self._todos(request)
        return {
            "todos": todos,
            "has_todos": bool(todos),
            **self._stats(todos),
        }

    @action
    def add_todo(self, request, title="", **params):
        clean_title = str(title).strip()
        if not clean_title:
            return self.action_response(
                toast={
                    "type": "error",
                    "title": "Missing title",
                    "message": "Todo title is required.",
                }
            )

        todos = self._todos(request)
        todo = {
            "id": uuid4().hex[:8],
            "title": clean_title,
            "done": False,
        }
        todos.append(todo)
        self._save_todos(request, todos)

        return self.action_response(
            html=self.render(
                request=request,
                relative_template_name="partials/item.html",
                context_updates={"todo": todo},
            ),
            signals={"title": ""},
            target="#todo-list",
            swap="append",
            transition=True,
            oob={
                "#todo-stats": self._render_stats(request, todos),
                "#todo-empty": self._render_empty(request, todos),
            },
            toast={
                "type": "success",
                "title": "Added",
                "message": f"{clean_title} added.",
            },
        )

    @action
    def toggle_todo(self, request, id="", **params):
        todos = self._todos(request)
        target = next((item for item in todos if item["id"] == id), None)
        if target is None:
            return self.action_response(
                toast={
                    "type": "error",
                    "title": "Not found",
                    "message": "Todo does not exist.",
                }
            )

        target["done"] = not bool(target["done"])
        self._save_todos(request, todos)

        return self.action_response(
            html=self.render(
                request=request,
                relative_template_name="partials/item.html",
                context_updates={"todo": target},
            ),
            target=f"#todo-{target['id']}",
            swap="outer",
            transition=True,
            oob={"#todo-stats": self._render_stats(request, todos)},
            toast={
                "type": "info",
                "title": "Updated",
                "message": "Marked completed." if target["done"] else "Marked active.",
            },
        )

    @action
    def delete_todo(self, request, id="", **params):
        todos = self._todos(request)
        remaining = [item for item in todos if item["id"] != id]
        if len(remaining) == len(todos):
            return self.action_response(
                toast={
                    "type": "error",
                    "title": "Not found",
                    "message": "Todo does not exist.",
                }
            )

        self._save_todos(request, remaining)

        return self.action_response(
            target=f"#todo-{id}",
            swap="delete",
            transition=True,
            oob={
                "#todo-stats": self._render_stats(request, remaining),
                "#todo-empty": self._render_empty(request, remaining),
            },
            toast={"type": "warning", "title": "Removed", "message": "Todo deleted."},
        )

    @action
    def clear_completed(self, request, **params):
        todos = self._todos(request)
        remaining = [item for item in todos if not bool(item.get("done"))]
        self._save_todos(request, remaining)

        return self.action_response(
            html=self.render(
                request=request,
                relative_template_name="partials/items.html",
                context_updates={"todos": remaining},
            ),
            target="#todo-list",
            swap="inner",
            transition=True,
            oob={
                "#todo-stats": self._render_stats(request, remaining),
                "#todo-empty": self._render_empty(request, remaining),
            },
            toast={
                "type": "success",
                "title": "Cleaned",
                "message": "Completed todos cleared.",
            },
        )

    def _render_stats(self, request, todos):
        return self.render(
            request=request,
            relative_template_name="partials/stats.html",
            context_updates=self._stats(todos),
        )

    def _render_empty(self, request, todos):
        return self.render(
            request=request,
            relative_template_name="partials/empty.html",
            context_updates={"has_todos": bool(todos)},
        )

    def _stats(self, todos):
        total = len(todos)
        completed = len([item for item in todos if bool(item.get("done"))])
        active = total - completed
        return {
            "total": total,
            "completed": completed,
            "active": active,
        }

    def _todos(self, request):
        raw = request.session.get("todos", [])
        if not isinstance(raw, list):
            return []

        todos = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            todo_id = str(item.get("id", "")).strip()
            title = str(item.get("title", "")).strip()
            if not todo_id or not title:
                continue
            todos.append(
                {"id": todo_id, "title": title, "done": bool(item.get("done"))}
            )
        return todos

    def _save_todos(self, request, todos):
        request.session["todos"] = todos
