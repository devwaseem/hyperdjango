import Alpine from "alpinejs";
import morph from "@alpinejs/morph";
import morphdom from "morphdom";
import { toast } from "vanilla-sonner";
import "vanilla-sonner/style.css";

Alpine.plugin(morph);

if (!(window as any).Alpine) {
  (window as any).Alpine = Alpine;
}

if (!(window as any).morphdom) {
  (window as any).morphdom = morphdom;
}

if (!(window as any).__hyperToastBridgeBound) {
  const showToast = (payload: any) => {
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

    const type = String(payload.type || "").toLowerCase();
    const message = payload.message || payload.title || "Notification";
    const config: { duration?: number; action?: { label: string; onClick: () => void } } = {};

    if (typeof payload.duration === "number") {
      config.duration = payload.duration;
    }

    if (
      payload.action &&
      typeof payload.action.label === "string" &&
      typeof payload.action.onClick === "function"
    ) {
      config.action = {
        label: payload.action.label,
        onClick: payload.action.onClick,
      };
    }

    if (type === "success") {
      toast.success(message, config);
      return;
    }
    if (type === "info") {
      toast.info(message, config);
      return;
    }
    if (type === "warning") {
      toast.warning(message, config);
      return;
    }
    if (type === "error") {
      toast.error(message, config);
      return;
    }

    if (typeof payload.description === "string" && payload.description.length > 0) {
      toast.message(message, payload.description, config);
      return;
    }

    toast(message, config);
  };

  window.addEventListener("hyper:toast", (event: Event) => {
    const custom = event as CustomEvent;
    showToast(custom.detail);
  });

  (window as any).__hyperToastBridgeBound = true;
}

Alpine.start();
