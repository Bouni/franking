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
    | "printInternetmarke"
    | "purchaseInternetmarke"
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
        invoice.value = response;
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
        invoice.value = response;
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

  async function printInternetmarke(invoice_number: string) {
    isLoading.value = { id: invoice_number, action: "printInternetmarke" };
    try {
      const response = await api.post("/internetmarke/print", {
        invoice_number: invoice_number,
      });
      showToast("Internetmarke successfully printed!", "#8ac926", 3);
    } catch (err: any) {
      showToast(
        `Error printing Internetmarke: ${err.message || "Error printing Internetmarke"}`,
        "#ff595e",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  async function purchaseInternetmarke(invoice_id: string) {
    isLoading.value = { id: invoice_id, action: "purchaseInternetmarke" };

    try {
      const invoice = invoices.value.find((inv) => inv.id === invoice_id);
      const data = {
        ...invoice.customer,
        invoiceNumber: invoice.invoiceNumber,
      };
      const response = await api.post("/internetmarke/purchase", data);
      if (invoice) {
        invoice.internetmarke = true;
        showToast("Internetmarke successfully purchased!", "#8ac926", 3);
      } else {
        showToast("Invoice not found", "#ff595e", 10);
      }
      const response2 = await api.get("/internetmarke/balance");
      internetmarke.value = response2.data;
    } catch (err: any) {
      showToast(
        `Error purchasing Internetmarke: ${err.message || "Error purchasing Internetmarke"}`,
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
    printInternetmarke,
    purchaseInternetmarke,
    printInvoice,
    sendInvoice,
    updatePayments,
  };
});
