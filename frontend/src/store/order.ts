import { defineStore } from "pinia";
import { ref } from "vue";
import api from "@/plugins/axios";

export interface Product {
  id: string;
  name: string;
  unitPrice: number;
  category?: string;
  // Weight per piece in grams, for the shipping price
  weightG?: number;
  // Pieces in stock, null when the stock isn't tracked (unlimited)
  stock?: number | null;
  // More is on the way, due is a date (YYYY-MM-DD) or null when unknown
  restock?: { due: string | null } | null;
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

  // Reload in the background, a failure keeps the list that is shown
  async function refreshProducts() {
    try {
      const response = await api.get("/order/products");
      products.value = response.data;
      productsError.value = false;
    } catch {
      // The next refresh tries again
    }
  }

  async function fetchShipping(
    country: string,
    goodsG: number,
  ): Promise<Shipping | null> {
    try {
      const response = await api.get("/order/shipping", {
        params: { country, goods_g: goodsG },
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
    refreshProducts,
    fetchShipping,
    fetchRegions,
    submitOrder,
  };
});
