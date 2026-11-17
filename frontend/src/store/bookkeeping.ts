import { defineStore } from "pinia";
import { ref } from "vue";
import api from "@/plugins/axios";
import { useAppStore } from "@/store/app";

export type EntryKind = "income" | "expense";

// Fields of a manual entry, amounts gross in euros
export interface EntryData {
  kind: EntryKind;
  // Date as YYYY-MM-DD
  date: string;
  description: string;
  party: string;
  category: string;
  amount: number;
  // VAT included in the amount
  vat: number;
  note: string;
}

export interface Entry extends EntryData {
  id: number;
  has_receipt: boolean;
  receipt_name: string | null;
}

// Paid invoice from Invio, counted in the year it was paid
export interface InvoiceIncome {
  id: string;
  date: string;
  number: string;
  customer: string;
  amount: number;
  vat: number;
  method: string;
}

export interface Totals {
  invoices: number;
  other_income: number;
  income: number;
  expenses: number;
  expense_vat: number;
  categories: Record<string, number>;
  result: number;
}

export interface Bookkeeping {
  year: number;
  years: number[];
  invoices: InvoiceIncome[];
  income: Entry[];
  expenses: Entry[];
  totals: Totals;
}

type Action = "fetch" | "save" | "delete" | "receipt";

export const useBookkeepingStore = defineStore("bookkeeping", () => {
  const app = useAppStore();
  const data = ref<Bookkeeping | null>(null);
  const year = ref(new Date().getFullYear());
  const loading = ref<{ action: Action; id?: number } | null>(null);

  function fail(text: string, error: any) {
    app.showToast(
      `${text}: ${error.response?.data?.msg || error.message}`,
      "#ff595e",
      10,
    );
  }

  async function fetch() {
    loading.value = { action: "fetch" };
    try {
      const response = await api.get("/bookkeeping", {
        params: { year: year.value },
      });
      data.value = response.data;
    } catch (error: any) {
      fail("Error fetching the bookkeeping", error);
    } finally {
      loading.value = null;
    }
  }

  // Creates the entry without id, updates it otherwise. Returns the saved
  // entry, or null when it failed
  async function save(entry: EntryData, id?: number): Promise<Entry | null> {
    loading.value = { action: "save", id };
    try {
      const response = id
        ? await api.put(`/bookkeeping/entries/${id}`, entry)
        : await api.post("/bookkeeping/entries", entry);
      app.showToast("Entry saved!", "#8ac926", 3);
      return response.data;
    } catch (error: any) {
      fail("Error saving the entry", error);
      return null;
    } finally {
      loading.value = null;
    }
  }

  async function remove(id: number) {
    loading.value = { action: "delete", id };
    try {
      await api.delete(`/bookkeeping/entries/${id}`);
      app.showToast("Entry deleted!", "#8ac926", 3);
      await fetch();
    } catch (error: any) {
      fail("Error deleting the entry", error);
    } finally {
      loading.value = null;
    }
  }

  async function uploadReceipt(id: number, file: File) {
    loading.value = { action: "receipt", id };
    const form = new FormData();
    form.append("file", file);
    try {
      await api.post(`/bookkeeping/entries/${id}/receipt`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return true;
    } catch (error: any) {
      fail("Error uploading the receipt", error);
      return false;
    } finally {
      loading.value = null;
    }
  }

  async function removeReceipt(id: number) {
    loading.value = { action: "receipt", id };
    try {
      await api.delete(`/bookkeeping/entries/${id}/receipt`);
      return true;
    } catch (error: any) {
      fail("Error removing the receipt", error);
      return false;
    } finally {
      loading.value = null;
    }
  }

  function receiptUrl(id: number) {
    return `${api.defaults.baseURL}/bookkeeping/entries/${id}/receipt`;
  }

  function reportUrl(receipts: boolean) {
    const params = new URLSearchParams({
      year: String(year.value),
      receipts: String(receipts),
    });
    return `${api.defaults.baseURL}/bookkeeping/report?${params}`;
  }

  return {
    data,
    year,
    loading,
    fetch,
    save,
    remove,
    uploadReceipt,
    removeReceipt,
    receiptUrl,
    reportUrl,
  };
});
