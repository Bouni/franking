<template>
  <v-row>
    <v-col cols="12">
      <v-card>
        <v-data-table
          :headers="headers"
          :items="invoices"
          :loading="isLoading === 'fetchInvoices'"
        >
          <template v-slot:loading>
            <v-skeleton-loader type="table-row@10"></v-skeleton-loader>
          </template>
          <template #item.subtotal="{ value }">
            {{ value.toFixed(2) }} €
          </template>
          <template #item.status="{ value }">
            <v-chip size="small" :color="status_colors[value as keyof typeof status_colors]" variant="flat">
              {{ value }}
            </v-chip>
          </template>
          <template #item.checks="{ item }">
            <v-icon
              :color="
                item.items.some((i: any) => i.description.includes('Versand'))
                  ? 'green'
                  : 'yellow'
              "
              :icon="
                item.items.some((i: any) => i.description.includes('Versand'))
                  ? 'mdi-check-circle-outline'
                  : 'mdi-alert'
              "
              size="large"
            ></v-icon>
          </template>
          <template #item.customer.countryCode="{ value }">
            <span class="ms-2">{{ value }}</span>
            <span
              class="ml-4"
              :class="`fi fi-${value.toLowerCase()}`"
              style="border-radius: 2px"
            ></span>
          </template>
          <template #item.actions="{ item }">
            <v-tooltip text="Send invoice as e-mail">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  :disabled="item.status !== 'draft' || item.customer.email === ''"
                  :loading="isLoading === 'sendInvoice'"
                  class="ma-2"
                  color="lime-accent-3"
                  icon="mdi-email-fast"
                  @click="sendInvoice(item.id)"
                ></v-btn>
              </template>
            </v-tooltip>
            <v-tooltip text="Mark as paid">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  :disabled="item.status !== 'sent'"
                  :loading="isLoading === 'markInvoicePaid'"
                  class="ma-2"
                  color="green"
                  icon="mdi-currency-eur"
                  @click="markInvoicePaid(item.id)"
                ></v-btn>
              </template>
            </v-tooltip>
            <v-tooltip text="Purchase Internetmarke">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  :disabled="item.internetmarke"
                  :loading="isLoading === 'purchaseInternetmarke'"
                  class="ma-2"
                  color="blue-darken-1"
                  icon="mdi-postage-stamp"
                  @click="purchaseInternetmarke(item.id)"
                ></v-btn>
              </template>
            </v-tooltip>
            <v-tooltip text="Print Internetmarke">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  :disabled="!item.internetmarke"
                  :loading="isLoading === 'printInternetmarke'"
                  class="ma-2"
                  color="purple"
                  icon="mdi-printer"
                  @click="printInternetmarke(item.invoiceNumber)"
                ></v-btn>
              </template>
            </v-tooltip>
            <v-tooltip text="Print invoice">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  :disabled="item.status != 'paid'"
                  :loading="isLoading === 'printInvoice'"
                  class="ma-2"
                  color="red"
                  icon="mdi-printer-outline"
                  @click="printInvoice(item.id)"
                ></v-btn>
              </template>
            </v-tooltip>
          </template>
        </v-data-table>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { useAppStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { onMounted, computed } from "vue";

const appStore = useAppStore();
const { isLoading, invoices } = storeToRefs(appStore);
const {
  printInternetmarke,
  purchaseInternetmarke,
  markInvoicePaid,
  fetchInvoices,
  printInvoice,
  sendInvoice,
} = appStore;

const status_colors = {
  complete: "#ff7d5d",
  draft: "#242933",
  sent: "#28ebff",
  paid: "#62efbd",
  voided: "#1c212b"
} as const;

const headers = [
  { title: "Invoice number", key: "invoiceNumber", align: "start" },
  { title: "Shipping", key: "checks", align: "center", sortable: false },
  { title: "Status", key: "status", align: "center", sortable: false },
  { title: "Sum", key: "subtotal", align: "start" },
  { title: "Customer", key: "customer.name", align: "start" },
  { title: "Address", key: "customer.address", align: "start" },
  { title: "City", key: "customer.city", align: "start" },
  { title: "Postal code", key: "customer.postalCode", align: "start" },
  { title: "Country", key: "customer.countryCode", align: "start" },
  {
    title: "Actions",
    key: "actions",
    align: "center",
    sortable: false,
  }
] as const;

// Fetch data when the component loads
onMounted(() => {
  fetchInvoices();
});
</script>
