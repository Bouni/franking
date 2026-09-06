import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "@/plugins/axios";
import Toastify from "toastify-js";
import "toastify-js/src/toastify.css";

export const useOrderStore = defineStore("order", () => {
  // const internetmarke = ref({ balance: 0.0 });
  const products = ref<any[]>([]);

  const sleep = (ms: number) =>
    new Promise((resolve) => setTimeout(resolve, ms));

  // function updateInvoice(invoice_data: any) {
  //   invoices.value = invoices.value.map((inv) =>
  //     inv.id === invoice_data.id ? invoice_data : inv,
  //   );
  // }

  async function fetchProducts() {
    try {
      const response = await api.get("/order/products");
      products.value = response.data;
    } catch (err: any) {
      console.log("Error loading products");
    } finally {
      isLoading.value = null;
    }
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

  return {
    fetchProducts,
  };
});
