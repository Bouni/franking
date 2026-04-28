        showToast("No new paid invoices!", "#62efbd", 10)0
        showToast("No new paid invoices!", "#62efbd", 10)0
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
  const error = ref<string | null>(null);

  const sleep = (ms: number) =>
    new Promise((resolve) => setTimeout(resolve, ms));

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
        "#D32F2F",
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
        "#D32F2F",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  async function markInvoicePaid(invoice_id: string) {
    isLoading.value = { id: invoice_id, action: "markInvoicePaid" };

    try {
      await api.get(`/invoices/${invoice_id}/paid`);
      const invoice = invoices.value.find((inv) => inv.id === invoice_id);
      if (invoice) {
        invoice.status = "paid";
        showToast("Successfully marked Invoice as paid!", "#62efbd", 3);
      } else {
        showToast("Invoice not found", "#D32F2F", 10);
      }
    } catch (err: any) {
      showToast(
        `Error marking Invoice as paid: ${err.message || "Error marking Invoice as paid"}`,
        "#D32F2F",
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
      showToast("Successfully printed Invoice!", "#62efbd", 3);
    } catch (err: any) {
      showToast(
        `Error printing Invoice: ${err.message || "Error printing Invoice"}`,
        "#D32F2F",
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
        showToast("Successfully sent Invoice!", "#62efbd", 3);
      } else {
        showToast("Invoice not found", "#D32F2F", 10);
      }
    } catch (err: any) {
      showToast(
        `Error sending Invoice: ${err.message || "Error sending Invoice"}`,
        "#D32F2F",
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
      showToast("Internetmarke successfully printed!", "#62efbd", 3);
    } catch (err: any) {
      showToast(
        `Error printing Internetmarke: ${err.message || "Error printing Internetmarke"}`,
        "#D32F2F",
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
        showToast("Internetmarke successfully purchased!", "#62efbd", 3);
      } else {
        showToast("Invoice not found", "#D32F2F", 10);
      }
      const response2 = await api.get("/internetmarke/balance");
      internetmarke.value = response2.data;
    } catch (err: any) {
      showToast(
        `Error purchasing Internetmarke: ${err.message || "Error purchasing Internetmarke"}`,
        "#D32F2F",
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
          showToast(`Invoice ${inv.invoiceNumber} paid!`, "#62efbd", 10);
        });
        showToast("No new paid invoices!", "#62efbd", 10);
      } else {
      }
    } catch (err: any) {
      showToast(
        `Error updating payments: ${err.message || "Error updating payments"}`,
        "#D32F2F",
        10,
      );
    } finally {
      isLoading.value = null;
    }
  }

  async function dummy() {
    showToast("Dummy!", "#551188", 10);
  }
  
  return {
    internetmarke,
    invoices,
    error,
    isLoading,
    fetchBalance,
    fetchInvoices,
    markInvoicePaid,
    printInternetmarke,
    purchaseInternetmarke,
    printInvoice,
    sendInvoice,
    updatePayments,
    dummy
  };
});
