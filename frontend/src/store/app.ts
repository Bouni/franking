import { defineStore } from "pinia";
import Toastify from "toastify-js";
import { ref } from "vue";
import api from "@/plugins/axios";
import { useOrderStore } from "@/store/order";
import "toastify-js/src/toastify.css";

export interface LoadingState {
  id: number | string;
  action:
    | "fetchOutstanding"
    | "fetchInvoices"
    | "markInvoicePaid"
    | "markInvoiceComplete"
    | "printInvoice"
    | "sendInvoice"
    | "printLabel"
    | "createLabel"
    | "cancelLabel"
    | "updatePayments"
    | "fetchSettings"
    | "saveSettings"
    | "fetchStock"
    | "bookStock"
    | "expectStock";
}

export interface Settings {
  invoice_email_subject: string;
  invoice_email_body: string;
  tracking_email_enabled: boolean;
  tracking_email_subject: string;
  tracking_email_body: string;
  invoice_placeholders?: Record<string, string>;
  tracking_placeholders?: Record<string, string>;
}

export interface ExpectedDelivery {
  quantity: number;
  // Date as YYYY-MM-DD
  due: string | null;
  note: string;
}

export interface StockProduct {
  id: string;
  name: string;
  // null: not tracked, unlimited
  stock: number | null;
  // null: no delivery expected
  expected: ExpectedDelivery | null;
}

export interface StockEntry {
  at: string;
  product: string;
  change: number;
  quantity: number | null;
  reason: string;
  invoice: string | null;
  note: string;
}

export interface Stock {
  products: StockProduct[];
  history: StockEntry[];
}

export interface InvoiceEmail {
  subject: string;
  body: string;
  recipient?: string;
}

export interface Outstanding {
  // Labels Sendcloud hasn't invoiced yet ("Offene Versandkredite")
  open: number;
  unpaid: number;
  unpaid_count: number;
}

export const useAppStore = defineStore("app", () => {
  const sendcloudOutstanding = ref<Outstanding | null>(null);
  const invoices = ref<any[]>([]);
  const isLoading = ref<LoadingState | null>(null);
  const settings = ref<Settings | null>(null);
  const stock = ref<Stock | null>(null);
  const updateAvailable = ref(false);

  // Invio's invoice data has no customer and label, keep the ones we have
  function updateInvoice(invoice_data: any) {
    invoices.value = invoices.value.map((inv) =>
      inv.id === invoice_data.id ? { ...inv, ...invoice_data } : inv,
    );
  }

  function showToast(text: string, color: string, duration: number) {
    Toastify({
      text,
      duration: duration * 1000,
      gravity: "bottom",
      position: "center",
      style: {
        background: color,
        color: "#000",
      },
    }).showToast();
  }

  async function fetchInvoices() {
    isLoading.value = { id: "", action: "fetchInvoices" };

    try {
      const response = await api.get("/invoices");
      invoices.value = response.data.invoices;
    } catch (error: any) {
      showToast(
        `Error fetching Invoices: ${error.message || "Error fetching Invoices"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  // Reload the list without the loading state, so nothing flickers, and
  // announce invoices that got paid in the meantime
  async function refreshInvoices() {
    try {
      const response = await api.get("/invoices");
      const before = new Map(invoices.value.map((inv) => [inv.id, inv.status]));
      invoices.value = response.data.invoices;
      for (const inv of invoices.value) {
        const old = before.get(inv.id);
        if (old && old !== "paid" && inv.status === "paid") {
          showToast(`Invoice ${inv.invoiceNumber} paid!`, "#8ac926", 10);
        }
      }
    } catch {
      // The next poll tries again
    }
  }

  async function refreshStock() {
    try {
      const response = await api.get("/stock");
      stock.value = response.data;
    } catch {
      // The next poll tries again
    }
  }

  async function refreshOutstanding() {
    try {
      const response = await api.get("/sendcloud/outstanding");
      if (response.data.success) {
        sendcloudOutstanding.value = {
          open: response.data.open,
          unpaid: response.data.unpaid,
          unpaid_count: response.data.unpaid_count,
        };
      }
    } catch {
      // The next poll tries again
    }
  }

  // Payments, tracking and stock are also checked in the background, poll a
  // change counter and reload the data when it moved. Not everything moves the
  // counter (e.g. invoices edited in Invio), so reload everything when the last
  // full reload is too old as well. Only while the page is visible, so a tab
  // that was hidden for days catches up as soon as it is looked at.
  const PAYMENT_POLL_MS = 30_000;
  const FULL_REFRESH_MS = 5 * 60_000;
  let paymentChanges: number | null = null;
  let paymentPoll: ReturnType<typeof setInterval> | null = null;
  let lastFullRefresh = 0;
  let frontendVersion: string | null = null;

  async function pollPayments() {
    if (document.hidden) {
      return;
    }
    try {
      const response = await api.get("/payments/status");
      const { changes, frontend } = response.data;
      const changed = paymentChanges !== null && changes !== paymentChanges;
      const stale = Date.now() - lastFullRefresh >= FULL_REFRESH_MS;
      paymentChanges = changes;
      if (stale) {
        lastFullRefresh = Date.now();
      }
      frontendVersion ??= frontend;
      if (frontend && frontend !== frontendVersion) {
        updateAvailable.value = true;
      }
      if (changed || stale) {
        await Promise.all([
          refreshInvoices(),
          refreshStock(),
          useOrderStore().refreshProducts(),
          // Calls the Sendcloud API, and the counter says nothing about it
          stale ? refreshOutstanding() : null,
        ]);
      }
    } catch {
      // The next poll tries again
    }
  }

  function startPaymentWatch() {
    if (paymentPoll) {
      return;
    }
    // The components load their data when they are mounted
    lastFullRefresh = Date.now();
    pollPayments();
    paymentPoll = setInterval(pollPayments, PAYMENT_POLL_MS);
    document.addEventListener("visibilitychange", pollPayments);
  }

  function stopPaymentWatch() {
    if (paymentPoll) {
      clearInterval(paymentPoll);
      paymentPoll = null;
    }
    document.removeEventListener("visibilitychange", pollPayments);
  }

  async function markInvoicePaid(invoice_id: string, method: string) {
    isLoading.value = { id: invoice_id, action: "markInvoicePaid" };

    try {
      await api.post(`/invoices/mark/paid`, {
        invoice_id,
        method,
      });
      const response = await api.get(`/invoices/${invoice_id}`);
      const invoice = invoices.value.find((inv) => inv.id === invoice_id);
      if (invoice) {
        Object.assign(invoice, response.data);
        showToast("Successfully marked Invoice as paid!", "#8ac926", 3);
      } else {
        showToast("Invoice not found", "#ff595e", 10);
      }
    } catch (error: any) {
      showToast(
        `Error marking Invoice as paid: ${error.message || "Error marking Invoice as paid"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  async function markInvoiceComplete(invoice_id: string) {
    isLoading.value = { id: invoice_id, action: "markInvoiceComplete" };

    try {
      await api.post(`/invoices/mark/complete`, {
        invoice_id,
      });
      const response = await api.get(`/invoices/${invoice_id}`);
      const invoice = invoices.value.find((inv) => inv.id === invoice_id);
      if (invoice) {
        Object.assign(invoice, response.data);
        showToast("Successfully marked Invoice as complete!", "#8ac926", 3);
      } else {
        showToast("Invoice not found", "#ff595e", 10);
      }
    } catch (error: any) {
      showToast(
        `Error marking Invoice as complete: ${error.message || "Error marking Invoice as complete"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  async function printInvoice(invoice_id: string) {
    isLoading.value = { id: invoice_id, action: "printInvoice" };

    try {
      await api.post(`/invoices/print`, { invoice_id });
      showToast("Successfully printed Invoice!", "#8ac926", 3);
    } catch (error: any) {
      showToast(
        `Error printing Invoice: ${error.message || "Error printing Invoice"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  async function previewInvoiceEmail(
    invoice_id: string,
  ): Promise<InvoiceEmail | null> {
    // Shown as loading send button while the text is fetched
    isLoading.value = { id: invoice_id, action: "sendInvoice" };

    try {
      const response = await api.post(`/invoices/email/preview`, {
        invoice_id,
      });
      return response.data;
    } catch (error: any) {
      showToast(
        `Error loading email text: ${error.message || "Error loading email text"}`,
        "#ff595e",
        10,
      );
      return null;
    } finally {
      isLoading.value = null;
    }
  }

  async function sendInvoice(invoice_id: string, email?: InvoiceEmail) {
    isLoading.value = { id: invoice_id, action: "sendInvoice" };

    try {
      const response = await api.post(`/invoices/email`, {
        invoice_id,
        subject: email?.subject,
        body: email?.body,
      });
      const invoice = invoices.value.find((inv) => inv.id === invoice_id);
      if (response.data.debug) {
        showToast("Dry run (DEBUG): invoice email NOT sent", "#ffca3a", 5);
      } else if (invoice) {
        if (invoice.status === "draft") {
          invoice.status = "sent";
        }
        showToast("Successfully sent Invoice!", "#8ac926", 3);
      } else {
        showToast("Invoice not found", "#ff595e", 10);
      }
    } catch (error: any) {
      showToast(
        `Error sending Invoice: ${error.message || "Error sending Invoice"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  async function printLabel(invoice_number: string) {
    isLoading.value = { id: invoice_number, action: "printLabel" };
    try {
      const response = await api.post("/shipping/print", {
        invoice_number,
      });
      if (!response.data.success) {
        throw new Error(response.data.msg);
      }
      showToast("Shipping label successfully printed!", "#8ac926", 3);
    } catch (error: any) {
      showToast(
        `Error printing shipping label: ${error.message || "Error printing shipping label"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  async function fetchOutstanding() {
    isLoading.value = { id: "", action: "fetchOutstanding" };

    try {
      const response = await api.get("/sendcloud/outstanding");
      if (!response.data.success) {
        throw new Error(response.data.msg);
      }
      sendcloudOutstanding.value = {
        open: response.data.open,
        unpaid: response.data.unpaid,
        unpaid_count: response.data.unpaid_count,
      };
    } catch (error: any) {
      showToast(
        `Error fetching Sendcloud invoices: ${error.message || "Error fetching Sendcloud invoices"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  async function createLabel(invoice_id: string) {
    isLoading.value = { id: invoice_id, action: "createLabel" };

    try {
      const response = await api.post("/shipping/label", {
        invoice_id,
      });
      if (!response.data.success) {
        throw new Error(response.data.msg);
      }
      const invoice = invoices.value.find((inv) => inv.id === invoice_id);
      if (invoice) {
        invoice.label = response.data.label;
        showToast("Shipping label successfully created!", "#8ac926", 3);
      } else {
        showToast("Invoice not found", "#ff595e", 10);
      }
      const trackingEmail = response.data.tracking_email;
      if (trackingEmail) {
        showToast(
          trackingEmail.msg,
          trackingEmail.sent ? "#8ac926" : "#ffca3a",
          trackingEmail.sent ? 3 : 10,
        );
      }
    } catch (error: any) {
      showToast(
        `Error creating shipping label: ${error.message || "Error creating shipping label"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
    fetchOutstanding();
  }

  async function cancelLabel(invoice_number: string) {
    isLoading.value = { id: invoice_number, action: "cancelLabel" };
    try {
      const response = await api.post("/shipping/cancel", {
        invoice_number,
      });
      if (!response.data.success) {
        throw new Error(response.data.msg);
      }
      const invoice = invoices.value.find(
        (inv) => inv.invoiceNumber === invoice_number,
      );
      if (invoice) {
        invoice.label = null;
      }
      showToast(response.data.msg, "#8ac926", 5);
    } catch (error: any) {
      showToast(
        `Error cancelling shipping label: ${error.message || "Error cancelling shipping label"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
    fetchOutstanding();
  }

  async function updatePayments() {
    isLoading.value = { id: "", action: "updatePayments" };

    try {
      const response = await api.get("/payments/check");
      if (response.data.paid > 0) {
        for (const inv of response.data.paid_invoices) {
          updateInvoice(inv.invoice_data);
          showToast(`Invoice ${inv.invoiceNumber} paid!`, "#8ac926", 10);
        }
      } else {
        showToast("No new paid invoices!", "#2196f3", 10);
      }
      for (const inv of response.data.partial_invoices ?? []) {
        showToast(
          `Invoice ${inv.invoiceNumber}: only ${inv.received.toFixed(2)} of ${inv.total.toFixed(2)} € received, it stays open`,
          "#ffca3a",
          15,
        );
      }
      for (const problem of response.data.problems ?? []) {
        showToast(problem, "#ffca3a", 15);
      }
    } catch (error: any) {
      showToast(
        `Error updating payments: ${error.message || "Error updating payments"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  async function fetchStock() {
    isLoading.value = { id: "", action: "fetchStock" };
    try {
      const response = await api.get("/stock");
      stock.value = response.data;
    } catch (error: any) {
      showToast(
        `Error fetching stock: ${error.message || "Error fetching stock"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  // kind "receive" books in new goods, "correct" sets the counted stock
  // (quantity null stops tracking the product)
  async function bookStock(
    kind: "receive" | "correct",
    productId: string,
    quantity: number | null,
    note: string,
  ) {
    isLoading.value = { id: productId, action: "bookStock" };
    try {
      const response = await api.post(`/stock/${kind}`, {
        productId,
        quantity,
        note,
      });
      stock.value = response.data;
      showToast("Stock updated!", "#8ac926", 3);
      return true;
    } catch (error: any) {
      showToast(
        `Error updating stock: ${error.response?.data?.msg || error.message}`,
        "#ff595e",
        10,
      );
      return false;
    } finally {
      isLoading.value = null;
    }
  }

  // A null delivery removes the expected delivery of the product
  async function expectStock(
    productId: string,
    delivery: ExpectedDelivery | null,
  ) {
    isLoading.value = { id: productId, action: "expectStock" };
    try {
      const response = await api.post("/stock/expect", {
        productId,
        quantity: delivery?.quantity ?? null,
        due: delivery?.due ?? null,
        note: delivery?.note ?? "",
      });
      stock.value = response.data;
      showToast(
        delivery ? "Delivery expected!" : "Expected delivery removed!",
        "#8ac926",
        3,
      );
      return true;
    } catch (error: any) {
      showToast(
        `Error saving the expected delivery: ${error.response?.data?.msg || error.message}`,
        "#ff595e",
        10,
      );
      return false;
    } finally {
      isLoading.value = null;
    }
  }

  async function fetchSettings() {
    isLoading.value = { id: "", action: "fetchSettings" };

    try {
      const response = await api.get("/settings");
      settings.value = response.data;
    } catch (error: any) {
      showToast(
        `Error fetching settings: ${error.message || "Error fetching settings"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  async function saveSettings(data: Settings) {
    isLoading.value = { id: "", action: "saveSettings" };

    try {
      const response = await api.put("/settings", data);
      settings.value = { ...settings.value, ...response.data };
      showToast("Settings saved!", "#8ac926", 3);
    } catch (error: any) {
      showToast(
        `Error saving settings: ${error.response?.data?.msg || error.message}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  return {
    stock,
    fetchStock,
    bookStock,
    expectStock,
    sendcloudOutstanding,
    updateAvailable,
    startPaymentWatch,
    stopPaymentWatch,
    settings,
    fetchSettings,
    saveSettings,
    invoices,
    isLoading,
    fetchInvoices,
    markInvoicePaid,
    markInvoiceComplete,
    printLabel,
    fetchOutstanding,
    createLabel,
    cancelLabel,
    printInvoice,
    previewInvoiceEmail,
    sendInvoice,
    updatePayments,
  };
});
