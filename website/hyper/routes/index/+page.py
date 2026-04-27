import time

from hyper.layouts.base import BaseLayout
from hyper.shared.seo import page_json_ld, seo_context, site_json_ld
from hyperdjango.actions import Delete, Event, HTML, Signal, Toast, action

# In-memory demo state (restarts with server)
STATE = {
    "todos": [
        {"id": 1, "title": "Configure HyperDjango", "done": True},
        {"id": 2, "title": "Implement partial swaps", "done": False},
        {"id": 3, "title": "Deploy to production", "done": False},
    ],
    "search_data": [
        "How to use HyperDjango",
        "Configuring Alpine.js with Django",
        "Fast partial swaps with Hyper",
        "Zero-JS interactivity examples",
        "Hypermedia-driven architecture",
        "Django templates vs React",
        "The simplicity of TUI design",
        "Terminal brutalism guidelines",
    ],
    "inline_text": "Click here to edit this text directly from the server.",
}


class PageView(BaseLayout):
    def __init__(self) -> None:
        super().__init__(title="HyperDjango | Modern Web Apps")

    def get(self, request, **params):
        stats = self._todo_stats(STATE["todos"])
        return {
            **seo_context(
                title="HyperDjango | Modern Web Apps",
                description=(
                    "HyperDjango is a server-driven Django framework for building interactive web apps without a separate SPA frontend."
                ),
                path="/",
                json_ld=[
                    *site_json_ld(),
                    page_json_ld(
                        title="HyperDjango | Modern Web Apps",
                        description=(
                            "HyperDjango is a server-driven Django framework for building interactive web apps without a separate SPA frontend."
                        ),
                        path="/",
                    ),
                ],
            ),
            "todos": STATE["todos"],
            **stats,
            "search_results": [],
            "inline_text": STATE["inline_text"],
            "editing": False,
        }

    # -- TODO ACTIONS --
    @action
    def add_todo(self, request, title=None, **kwargs):
        if not title:
            return []
        new_todo = {
            "id": len(STATE["todos"]) + 1,
            "title": title,
            "done": False,
        }
        STATE["todos"].append(new_todo)
        item_html = self.render(
            request=request,
            relative_template_name="partials/todo_item.html",
            context_updates={"todo": new_todo},
        )
        return [
            HTML(content=item_html, target="#todo-list-demo", swap="append"),
            HTML(
                content=self._render_todo_stats(request), target="#todo-stats"
            ),
            HTML(
                content=self._render_todo_empty(request), target="#todo-empty"
            ),
            Toast(
                payload={
                    "type": "success",
                    "title": "Added",
                    "message": f"{new_todo['title']} created.",
                }
            ),
        ]

    @action
    def toggle_todo(self, request, id=None, **kwargs):
        if id is None:
            return []
        todo_id = int(id)
        updated_todo = None
        for t in STATE["todos"]:
            if t["id"] == todo_id:
                t["done"] = not t["done"]
                updated_todo = t
                break
        if updated_todo is None:
            return []
        html = self.render(
            request=request,
            relative_template_name="partials/todo_item.html",
            context_updates={"todo": updated_todo},
        )
        return [
            HTML(content=html, target=f"#todo-{updated_todo['id']}"),
            HTML(
                content=self._render_todo_stats(request), target="#todo-stats"
            ),
            Toast(
                payload={
                    "type": "info",
                    "title": "Updated",
                    "message": "Todo state changed.",
                }
            ),
        ]

    @action
    def delete_todo(self, request, id=None, **kwargs):
        if id is None:
            return []
        todo_id = int(id)
        STATE["todos"] = [t for t in STATE["todos"] if t["id"] != todo_id]
        return [
            Delete(target=f"#todo-{todo_id}"),
            Toast(
                payload={
                    "type": "warning",
                    "title": "Deleted",
                    "message": "Todo removed.",
                }
            ),
            HTML(
                content=self._render_todo_stats(request), target="#todo-stats"
            ),
            HTML(
                content=self._render_todo_empty(request), target="#todo-empty"
            ),
        ]

    # -- SEARCH ACTION --
    @action
    def search(self, request, q="", **kwargs):
        time.sleep(0.5)
        q_str = str(q).lower()
        results = (
            [item for item in STATE["search_data"] if q_str in item.lower()]
            if q_str
            else []
        )
        html = self.render(
            request=request,
            relative_template_name="partials/search_results.html",
            context_updates={"search_results": results, "q": q},
        )
        return [HTML(content=html, target="#search-results-demo")]

    # -- INLINE EDIT ACTIONS --
    @action
    def edit_inline(self, request, **kwargs):
        html = self.render(
            request=request,
            relative_template_name="partials/inline_editor.html",
            context_updates={
                "editing": True,
                "inline_text": STATE["inline_text"],
            },
        )
        return [HTML(content=html, target="#inline-editor-demo")]

    @action
    def save_inline(self, request, text=None, **kwargs):
        if text is not None:
            STATE["inline_text"] = text
        html = self.render(
            request=request,
            relative_template_name="partials/inline_editor.html",
            context_updates={
                "editing": False,
                "inline_text": STATE["inline_text"],
            },
        )
        return [HTML(content=html, target="#inline-editor-demo")]

    @action
    def upload_demo(self, request, **kwargs):
        uploaded = request.FILES.get("upload")
        if uploaded is None:
            html = self.render(
                request=request,
                relative_template_name="partials/upload_result.html",
                context_updates={
                    "error": "Choose a file before uploading.",
                    "uploaded_name": "",
                    "uploaded_size_kb": "",
                    "content_type": "",
                },
            )
            return [HTML(content=html, target="#upload-result-demo")]

        size_kb = max(1, round(uploaded.size / 1024))
        html = self.render(
            request=request,
            relative_template_name="partials/upload_result.html",
            context_updates={
                "error": "",
                "uploaded_name": uploaded.name,
                "uploaded_size_kb": size_kb,
                "content_type": uploaded.content_type
                or "application/octet-stream",
            },
        )
        return [
            HTML(content=html, target="#upload-result-demo"),
            Toast(
                payload={
                    "type": "success",
                    "title": "Upload complete",
                    "message": f"Received {uploaded.name}.",
                }
            ),
        ]

    @action
    def increment_signal_demo(self, request, count=0, **kwargs):
        next_count = int(count) + 1
        return [
            Signal(name="count", value=next_count),
            Signal(
                name="status",
                value=f"Synced from server at count {next_count}",
            ),
        ]

    @action
    def run_agent_stream(self, request, prompt="", **kwargs):
        user_prompt = (
            str(prompt).strip()
            or "Explain how HyperDjango streams server events to the UI."
        )
        yield HTML(content="", target="#agent-thread-demo", swap="inner")
        yield HTML(
            content=self.render(
                request=request,
                relative_template_name="partials/agent_user_message.html",
                context_updates={"prompt": user_prompt},
            ),
            target="#agent-thread-demo",
            swap="append",
        )
        yield Event(name="agent:scroll", payload={})
        yield HTML(
            content=self.render(
                request=request,
                relative_template_name="partials/agent_log_shell.html",
            ),
            target="#agent-thread-demo",
            swap="append",
        )
        yield Event(name="agent:scroll", payload={})
        feed = [
            (
                "plan",
                f"Mapping the request into an execution plan for: {user_prompt}",
            ),
            (
                "tool",
                "Scanning route partials, action handlers, and SSE targets",
            ),
            (
                "write",
                "Preparing the streamed chat patches for tool output and final response",
            ),
            ("test", "Running the example checks before sending the answer"),
            ("test", "Checks passed. Starting final response stream"),
        ]

        for kind, message in feed:
            time.sleep(1.15)
            yield HTML(
                content=self.render(
                    request=request,
                    relative_template_name="partials/agent_log_chunk.html",
                    context_updates={
                        "kind": kind,
                        "message": message,
                    },
                ),
                target="#agent-log-text",
                swap="inner",
            )
            yield Event(name="agent:scroll", payload={})

        yield HTML(
            content=self.render(
                request=request,
                relative_template_name="partials/agent_log_shell_done.html",
            ),
            target="#agent-tool-message",
        )
        yield Event(name="agent:scroll", payload={})
        yield HTML(
            content=self.render(
                request=request,
                relative_template_name="partials/agent_log_chunk.html",
                context_updates={
                    "kind": "test",
                    "message": "Checks passed. Starting final response stream",
                },
            ),
            target="#agent-log-text",
            swap="inner",
        )
        yield Event(name="agent:scroll", payload={})

        yield HTML(
            content=self.render(
                request=request,
                relative_template_name="partials/agent_assistant_shell.html",
            ),
            target="#agent-thread-demo",
            swap="append",
        )
        yield Event(name="agent:scroll", payload={})

        response = (
            "I parsed your prompt and turned it into a small execution plan. "
            "Then the server streamed each tool phase into a single evolving status bubble instead of stacking separate lines. "
            "Once the checks passed, the assistant message appeared and the answer started streaming into that bubble chunk by chunk. "
            f"That gives you a chat flow that still exposes live server work for prompts like: '{user_prompt}'."
        )
        chunks = [segment + " " for segment in response.split()]

        if chunks:
            chunks[-1] = chunks[-1].rstrip()

        for chunk in chunks:
            time.sleep(0.055)
            yield HTML(
                content=self.render(
                    request=request,
                    relative_template_name="partials/agent_response_chunk.html",
                    context_updates={"chunk": chunk},
                ),
                target="#agent-response-demo",
                swap="append",
            )
            yield Event(name="agent:scroll", payload={})
        yield Toast(
            payload={
                "type": "success",
                "title": "Agent finished",
                "message": "The chat streamed tool updates first, then the final answer over SSE.",
            }
        )

    def _todo_stats(self, todos):
        total = len(todos)
        completed = len([todo for todo in todos if todo["done"]])
        active = total - completed
        return {
            "todo_total": total,
            "todo_completed": completed,
            "todo_active": active,
        }

    def _render_todo_stats(self, request):
        return self.render(
            request=request,
            relative_template_name="partials/todo_stats.html",
            context_updates=self._todo_stats(STATE["todos"]),
        )

    def _render_todo_empty(self, request):
        return self.render(
            request=request,
            relative_template_name="partials/todo_empty.html",
            context_updates={"has_todos": bool(STATE["todos"])},
        )
