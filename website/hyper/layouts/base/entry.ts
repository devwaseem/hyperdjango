import Alpine from "alpinejs";
import hljs from "highlight.js/lib/core";
import javascript from "highlight.js/lib/languages/javascript";
import xml from "highlight.js/lib/languages/xml";
import python from "highlight.js/lib/languages/python";
import typescript from "highlight.js/lib/languages/typescript";
import "highlight.js/styles/github.css";
import { toast } from "vanilla-sonner";
import "vanilla-sonner/style.css";

hljs.registerLanguage("html", xml);
hljs.registerLanguage("django", xml);
hljs.registerLanguage("js", javascript);
hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("python", python);
hljs.registerLanguage("ts", typescript);
hljs.registerLanguage("typescript", typescript);

const highlightCodeBlocks = () => {
    for (const block of document.querySelectorAll("pre code")) {
        if (block instanceof HTMLElement) {
            hljs.highlightElement(block);
        }
    }
};

const scrollAgentThreadToBottom = () => {
    const thread = document.getElementById("agent-thread-demo");
    if (!(thread instanceof HTMLElement)) {
        return;
    }

    thread.scrollTop = thread.scrollHeight;

    let parent = thread.parentElement;
    while (parent) {
        const style = window.getComputedStyle(parent);
        const canScroll = [style.overflowY, style.overflow].some((value) =>
            ["auto", "scroll", "overlay"].includes(value),
        );

        if (canScroll) {
            parent.scrollTop = parent.scrollHeight;
            break;
        }

        parent = parent.parentElement;
    }
};

if (!(window as typeof window & { Alpine?: typeof Alpine }).Alpine) {
    (window as typeof window & { Alpine?: typeof Alpine }).Alpine = Alpine;
}

Alpine.data("uploadDemo", () => ({
    progress: 0,
    status: "idle | 0%",
    filename: "No file chosen",
    _bound: false,
    _expectUpload: false,
    init() {
        if (this._bound) {
            return;
        }
        this._bound = true;

        window.addEventListener("hyper:uploadProgress", (event: Event) => {
            const custom = event as CustomEvent<{ key?: string; progress?: number }>;
            if (custom.detail?.key !== "upload-demo") {
                return;
            }
            const percent = Math.round((custom.detail.progress ?? 0) * 100);
            this.progress = percent;
            this.status = `uploading | ${percent}%`;
        });

        window.addEventListener("hyper:afterRequest", (event: Event) => {
            const custom = event as CustomEvent<{ key?: string; ok?: boolean }>;
            if (custom.detail?.key !== "upload-demo") {
                return;
            }
            if (!this._expectUpload) {
                this.progress = 0;
                this.status = "error | 0%";
                return;
            }
            if (custom.detail.ok) {
                this.progress = 100;
                this.status = "done | 100%";
                return;
            }
            this.status = "error | 0%";
        });
    },
    reset(formSelector?: string) {
        const form =
            typeof formSelector === "string"
                ? document.querySelector<HTMLFormElement>(formSelector)
                : null;
        const input = form?.querySelector<HTMLInputElement>('input[type="file"][name="upload"]');
        const hasFile = !!input?.files?.length;
        this.filename = input?.files?.[0]?.name || "No file chosen";

        this._expectUpload = hasFile;
        this.progress = 0;
        this.status = hasFile ? "starting | 0%" : "error | 0%";
    },
}));

if (!(window as typeof window & { __hyperToastBridgeBound?: boolean }).__hyperToastBridgeBound) {
    const showToast = (payload: unknown) => {
        if (payload == null) {
            return;
        }

        if (typeof payload === "string") {
            toast(payload);
            return;
        }

        if (typeof payload !== "object") {
            toast(String(payload));
            return;
        }

        const data = payload as {
            type?: string;
            title?: string;
            message?: string;
            duration?: number;
            action?: { label?: string; onClick?: () => void };
        };
        const type = String(data.type || "").toLowerCase();
        const title = data.title || data.message || "Notification";
        const message = data.title && data.message ? data.message : undefined;
        const config: {
            duration?: number;
            action?: { label: string; onClick: () => void };
        } = {};

        if (typeof data.duration === "number") {
            config.duration = data.duration;
        }

        if (
            data.action &&
            typeof data.action.label === "string" &&
            typeof data.action.onClick === "function"
        ) {
            config.action = {
                label: data.action.label,
                onClick: data.action.onClick,
            };
        }

        if (message) {
            toast.message(title, message, config);
            return;
        }

        if (type === "success") {
            toast.success(title, config);
            return;
        }
        if (type === "info") {
            toast.info(title, config);
            return;
        }
        if (type === "warning") {
            toast.warning(title, config);
            return;
        }
        if (type === "error") {
            toast.error(title, config);
            return;
        }

        toast(title, config);
    };

    const originalDispatchEvent = window.dispatchEvent.bind(window);
    window.dispatchEvent = ((event: Event) => {
        if (event.type === "hyper:toast") {
            const custom = event as CustomEvent;
            showToast(custom.detail);
        }
        return originalDispatchEvent(event);
    }) as typeof window.dispatchEvent;

    (
        window as typeof window & {
            __hyperToastBridgeBound?: boolean;
            __showHyperToast?: (payload: unknown) => void;
        }
    ).__showHyperToast = showToast;

    (window as typeof window & { __hyperToastBridgeBound?: boolean }).__hyperToastBridgeBound = true;
}

Alpine.start();
highlightCodeBlocks();

window.addEventListener("agent:scroll", () => {
    queueMicrotask(scrollAgentThreadToBottom);
});
