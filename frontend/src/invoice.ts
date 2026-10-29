// Helpers shared by the invoice table and the invoice cards

// colors from https://coolors.co/palette/ff595e-ffca3a-8ac926-1982c4-6a4c93
export const statusColors = {
  complete: "#7209b7",
  draft: "#1982c4",
  sent: "#ffca3a",
  paid: "#8ac926",
  voided: "#8da9c4",
} as const;

export type InvoiceStatus = keyof typeof statusColors;

export function statusColor(status: string) {
  return statusColors[status as InvoiceStatus];
}

export function formatPrice(value: number) {
  return `${(value ?? 0).toFixed(2)} €`;
}

export function formatDate(value: string) {
  return value ? new Date(value).toLocaleDateString("de-DE") : "";
}

export function paymentMethod(invoice: any): string | undefined {
  return invoice.statusHistory?.find((entry: any) => entry.paymentMethod)
    ?.paymentMethod;
}

// Shipping costs are an invoice item with "Versand" or "Shipping" in the
// description, so only flag invoices that have no such item at all
const shippingPattern = /versand|shipping/i;

export function hasShipping(invoice: any) {
  return (invoice.items ?? []).some((i: any) =>
    shippingPattern.test(i.description ?? ""),
  );
}

// Sendcloud tracking phases, each with its own color and icon. Events
// without a phase (phase "none") are exceptions, colored by their severity.
const trackingPhases: Record<string, { color: string; icon: string }> = {
  announcing: { color: "#76839b", icon: "mdi-upload-network" },
  announced: { color: "#457b9d", icon: "mdi-check-network" },
  ready_to_send: { color: "#6a4c93", icon: "mdi-package-variant" },
  labelled: { color: "#4267ac", icon: "mdi-label" },
  in_transit: { color: "#1982c4", icon: "mdi-truck-delivery" },
  out_for_delivery: { color: "#00918e", icon: "mdi-truck-fast" },
  ready_for_pickup: { color: "#ffca3a", icon: "mdi-store-marker" },
  at_service_point: { color: "#ffca3a", icon: "mdi-store-marker" },
  delivered: { color: "#5a9e1b", icon: "mdi-package-variant-closed-check" },
  returned: { color: "#ff924c", icon: "mdi-keyboard-return" },
  returned_to_sender: { color: "#ff924c", icon: "mdi-keyboard-return" },
  cancelled: { color: "#6c757d", icon: "mdi-cancel" },
};

// Unknown phases still get a color of their own, stable per name
const fallbackColors = ["#9c6644", "#b5179e", "#3a86ff", "#2a9d8f", "#e76f51"];

export function trackingLook(phase?: string, statusType?: string | null) {
  if (statusType === "error") {
    return { color: "#e63946", icon: "mdi-alert-octagon" };
  }
  if (!phase || phase === "none") {
    return statusType === "warning"
      ? { color: "#d95d0f", icon: "mdi-alert" }
      : { color: "#76839b", icon: "mdi-information" };
  }
  const known = trackingPhases[phase];
  if (known) {
    return statusType === "warning"
      ? { color: known.color, icon: "mdi-alert" }
      : known;
  }
  const hash = [...phase].reduce((h, c) => h + (c.codePointAt(0) ?? 0), 0);
  return {
    color: fallbackColors[hash % fallbackColors.length],
    icon: "mdi-map-marker-path",
  };
}

// "ready_to_send" -> "Ready to send", "none" -> ""
export function readable(value?: string | null) {
  if (!value || value === "none") {
    return "";
  }
  const text = value.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}
