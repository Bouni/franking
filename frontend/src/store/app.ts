import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "@/plugins/axios";
import Toastify from 'toastify-js'
import "toastify-js/src/toastify.css"

export const useAppStore = defineStore("app", () => {
  // State (ref)
  const internetmarke = ref({ balance: 0.0 });
  const invoices = ref<any[]>([]);
  const isLoading = ref<string|boolean>(false);
  const error = ref<string | null>(null);

  async function fetchBalance() {
    isLoading.value = "fetchBalance";
    error.value = null;

    try {
      const response = await api.get("/internetmarke/balance");
      internetmarke.value = response.data;
    } catch (err: any) {
      error.value = err.message || "Failed to fetch balance";
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchInvoices() {
    isLoading.value = "fetchInvoices";
    error.value = null;

    try {
      const response = await api.get("/invoices");
      invoices.value = response.data.invoices;
    } catch (err: any) {
      error.value = err.message || "Failed to fetch invoices";
    } finally {
      isLoading.value = false;
    }
  }

  async function markInvoicePaid(invoice_id: string) {
    isLoading.value = "markInvoicePaid";
    error.value = null;

    try {
      await api.get(`/invoices/${invoice_id}/paid`);
      const invoice = invoices.value.find(inv => inv.id === invoice_id);
      if(invoice) {
        invoice.status = "paid";
      } else {
        console.error("Invoice not found")
      }
    } catch (err: any) {
      error.value = err.message || "Failed to mark invoice paid";
    } finally {
      isLoading.value = false;
    }
  }

  async function printInvoice(invoice_id: string) {
    isLoading.value = "printInvoice";
    error.value = null;

    try {
      await api.post(`/invoices/print`, { invoice_id: invoice_id });
    } catch (err: any) {
      error.value = err.message || "Failed to print invoice";
    } finally {
      isLoading.value = false;
    }
  }
  
  async function sendInvoice(invoice_id: string) {
    isLoading.value = "sendInvoice";
    error.value = null;

    try {
      await api.post(`/invoices/email`, { invoice_id: invoice_id });
      const invoice = invoices.value.find(inv => inv.id === invoice_id);
      if(invoice) {
        invoice.status = "sent";
      } else {
        console.error("Invoice not found")
      }
    } catch (err: any) {
      error.value = err.message || "Failed to send invoice";
    } finally {
      isLoading.value = false;
    }
  }

  async function printInternetmarke(invoice_number: string) {
    isLoading.value = "printInternetmarke";
    error.value = null;

    try {
      const response = await api.post("/internetmarke/print", {
        invoice_number: invoice_number,
      });
    } catch (err: any) {
      error.value = err.message || "Failed to print Internetmarke";
    } finally {
      isLoading.value = false;
    }
  }
  
  async function purchaseInternetmarke(invoice_id: string) {
    isLoading.value = "purchaseInternetmarke";
    error.value = null;

    try {
      const invoice = invoices.value.find(inv => inv.id === invoice_id);
      const data = {
        ...invoice.customer,
        invoiceNumber: invoice.invoiceNumber
      }
      const response = await api.post("/internetmarke/purchase", data
      );
      if(invoice) {
        invoice.internetmarke = true;
      } else {
        console.error("Invoice not found")
      }
      const response2 = await api.get("/internetmarke/balance");
      internetmarke.value = response2.data;
    } catch (err: any) {
      error.value = err.message || "Failed to purchase Internetmarke";
    } finally {
      isLoading.value = false;
    }
  }
  
  async function updatePayments() {
    isLoading.value = "updatePayments";
    error.value = null;

    try {
      const response = await api.get("/payments/check");
      response.data.paid_invoices.forEach((inv: any) => {
        Toastify({
          text: `Invoice ${inv.invoiceNumber} paid!`,
          duration: 3000,
          gravity: "top", 
          position: "right",
          style: {
            background: "#62efbd", // Your 'paid' color
            color: "#000"
          }
        }).showToast();
      });
    } catch (err: any) {
      error.value = err.message || "Failed to print Internetmarke";
    } finally {
      isLoading.value = false;
    }
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
    updatePayments
  };
});
