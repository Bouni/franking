import { defineStore } from "pinia";
import { ref } from "vue";
import api from "@/plugins/axios";

export interface Product {
  id: string;
  name: string;
  unitPrice: number;
  category?: string;
}

export interface Region {
  code: string;
  name: string;
}

export interface Shipping {
  name: string;
  price: number;
}

export const useOrderStore = defineStore("order", () => {
  const products = ref<Product[]>([]);
  const productsError = ref(false);

  async function fetchProducts() {
    productsError.value = false;
    try {
      const response = await api.get("/order/products");
      products.value = response.data;
    } catch {
      productsError.value = true;
      console.log("Error loading products");
    }
  }

  async function fetchShipping(country: string): Promise<Shipping | null> {
    try {
      const response = await api.get("/order/shipping", {
        params: { country },
      });
      return response.data.success ? response.data : null;
    } catch {
      return null;
    }
  }

  // States/provinces, empty for countries that don't need one
  async function fetchRegions(country: string): Promise<Region[]> {
    try {
      const response = await api.get("/order/regions", {
        params: { country },
      });
      return response.data.regions;
    } catch {
      return [];
    }
  }

  // Returns null on success, otherwise an error message
  async function submitOrder(order: object): Promise<string | null> {
    try {
      const response = await api.post("/order/submit", order);
      return response.data.success ? null : response.data.msg;
    } catch (error: any) {
      return (
        error.response?.data?.msg ||
        "Sorry, something went wrong. Please try again later."
      );
    }
  }

  return {
    products,
    productsError,
    fetchProducts,
    fetchShipping,
    fetchRegions,
    submitOrder,
  };
});
