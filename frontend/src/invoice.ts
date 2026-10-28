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
