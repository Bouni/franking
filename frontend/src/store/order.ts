import { defineStore } from "pinia";
import { ref } from "vue";
import api from "@/plugins/axios";

export const useOrderStore = defineStore("order", () => {
  // const internetmarke = ref({ balance: 0.0 });
  const products = ref<any[]>([]);

  // function updateInvoice(invoice_data: any) {
  //   invoices.value = invoices.value.map((inv) =>
  //     inv.id === invoice_data.id ? invoice_data : inv,
  //   );
  // }

  async function fetchProducts() {
    try {
      const response = await api.get("/order/products");
      products.value = response.data;
    } catch {
      console.log("Error loading products");
    }
  }

  return {
    fetchProducts,
  };
});
