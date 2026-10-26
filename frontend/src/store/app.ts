import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "@/plugins/axios";
import Toastify from "toastify-js";
import "toastify-js/src/toastify.css";

export interface LoadingState {
  id: number | string;
  action:
    | "fetchBalance"
    | "fetchInvoices"
    | "markInvoicePaid"
    | "markInvoiceComplete"
    | "printInvoice"
    | "sendInvoice"
    | "printLabel"
    | "createLabel"
    | "cancelLabel"
    | "updatePayments";
}

export const useAppStore = defineStore("app", () => {
  const internetmarke = ref({ balance: 0.0 });
  const invoices = ref<any[]>([]);
  const isLoading = ref<LoadingState | null>(null);

  const sleep = (ms: number) =>
    new Promise((resolve) => setTimeout(resolve, ms));

  function updateInvoice(invoice_data: any) {
    invoices.value = invoices.value.map((inv) =>
      inv.id === invoice_data.id ? invoice_data : inv,
    );
  }

  function showToast(text: string, color: string, duration: number) {
    Toastify({
      text: text,
      duration: duration * 1000,
      gravity: "bottom",
      position: "center",
      style: {
        background: color,
        color: "#000",
      },
    }).showToast();
  }

  async function fetchBalance() {
    isLoading.value = { id: "", action: "fetchBalance" };

    try {
      const response = await api.get("/internetmarke/balance");
      internetmarke.value = response.data;
    } catch (err: any) {
      showToast(
        `Error fetching Balance: ${err.message || "Error fetching Balance"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  async function fetchInvoices() {
    isLoading.value = { id: "", action: "fetchInvoices" };

    try {
      const response = await api.get("/invoices");
      invoices.value = response.data.invoices;
    } catch (err: any) {
      showToast(
        `Error fetching Invoices: ${err.message || "Error fetching Invoices"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  async function markInvoicePaid(invoice_id: string, method: string) {
    isLoading.value = { id: invoice_id, action: "markInvoicePaid" };

    try {
      await api.post(`/invoices/mark/paid`, {
        invoice_id: invoice_id,
        method: method,
      });
      const response = await api.get(`/invoices/${invoice_id}`);
      const invoice = invoices.value.find((inv) => inv.id === invoice_id);
      if (invoice) {
        Object.assign(invoice, response.data);
        showToast("Successfully marked Invoice as paid!", "#8ac926", 3);
      } else {
        showToast("Invoice not found", "#ff595e", 10);
      }
    } catch (err: any) {
      showToast(
        `Error marking Invoice as paid: ${err.message || "Error marking Invoice as paid"}`,
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
        invoice_id: invoice_id,
      });
      const response = await api.get(`/invoices/${invoice_id}`);
      const invoice = invoices.value.find((inv) => inv.id === invoice_id);
      if (invoice) {
        Object.assign(invoice, response.data);
        showToast("Successfully marked Invoice as complete!", "#8ac926", 3);
      } else {
        showToast("Invoice not found", "#ff595e", 10);
      }
    } catch (err: any) {
      showToast(
        `Error marking Invoice as complete: ${err.message || "Error marking Invoice as complete"}`,
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
      await api.post(`/invoices/print`, { invoice_id: invoice_id });
      showToast("Successfully printed Invoice!", "#8ac926", 3);
    } catch (err: any) {
      showToast(
        `Error printing Invoice: ${err.message || "Error printing Invoice"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  async function sendInvoice(invoice_id: string) {
    isLoading.value = { id: invoice_id, action: "sendInvoice" };

    try {
      await api.post(`/invoices/email`, { invoice_id: invoice_id });
      const invoice = invoices.value.find((inv) => inv.id === invoice_id);
      if (invoice) {
        invoice.status = "sent";
        showToast("Successfully sent Invoice!", "#8ac926", 3);
      } else {
        showToast("Invoice not found", "#ff595e", 10);
      }
    } catch (err: any) {
      showToast(
        `Error sending Invoice: ${err.message || "Error sending Invoice"}`,
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
        invoice_number: invoice_number,
      });
      if (!response.data.success) throw new Error(response.data.msg);
      showToast("Shipping label successfully printed!", "#8ac926", 3);
    } catch (err: any) {
      showToast(
        `Error printing shipping label: ${err.message || "Error printing shipping label"}`,
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
        invoice_id: invoice_id,
      });
      if (!response.data.success) throw new Error(response.data.msg);
      const invoice = invoices.value.find((inv) => inv.id === invoice_id);
      if (invoice) {
        invoice.label = response.data.label;
        showToast("Shipping label successfully created!", "#8ac926", 3);
      } else {
        showToast("Invoice not found", "#ff595e", 10);
      }
      const response2 = await api.get("/internetmarke/balance");
      internetmarke.value = response2.data;
    } catch (err: any) {
      showToast(
        `Error creating shipping label: ${err.message || "Error creating shipping label"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  async function cancelLabel(invoice_number: string) {
    isLoading.value = { id: invoice_number, action: "cancelLabel" };
    try {
      const response = await api.post("/shipping/cancel", {
        invoice_number: invoice_number,
      });
      if (!response.data.success) throw new Error(response.data.msg);
      const invoice = invoices.value.find(
        (inv) => inv.invoiceNumber === invoice_number,
      );
      if (invoice) invoice.label = null;
      showToast(response.data.msg, "#8ac926", 5);
    } catch (err: any) {
      showToast(
        `Error cancelling shipping label: ${err.message || "Error cancelling shipping label"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  async function updatePayments() {
    isLoading.value = { id: "", action: "updatePayments" };

    try {
      const response = await api.get("/payments/check");
      if (response.data.paid > 0) {
        response.data.paid_invoices.forEach((inv: any) => {
          updateInvoice(inv.invoice_data);
          showToast(`Invoice ${inv.invoiceNumber} paid!`, "#8ac926", 10);
        });
      } else {
        showToast("No new paid invoices!", "##2196f3", 10);
      }
    } catch (err: any) {
      showToast(
        `Error updating payments: ${err.message || "Error updating payments"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  return {
    internetmarke,
    invoices,
    isLoading,
    fetchBalance,
    fetchInvoices,
    markInvoicePaid,
    markInvoiceComplete,
    printLabel,
    createLabel,
    cancelLabel,
    printInvoice,
    sendInvoice,
    updatePayments,
  };
});
