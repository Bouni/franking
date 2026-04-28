<template>
  <v-row>
    <v-row class="mb-4">
      <v-col v-for="(color, state) in status_colors" :key="state" cols="auto">
        <v-switch
          v-model="selectedStates"
          :label="state"
          :value="state"
          :color="color"
          hide-details
        ></v-switch>
      </v-col>
      <v-col>
        <v-btn
          color="primary"
          class="px-4 mt-3 ml-5"
          :loading="isLoading?.action === 'updatePayments'"
          @click="updatePayments()"
        >
          <img
            src="@/assets/Sparkasse.svg"
            width="20"
            height="20"
            class="mr-2"
            alt=""
          />
          <span class="mx-1">Update</span>
          <img
            src="@/assets/PayPal.svg"
            width="20"
            height="20"
            class="ml-2"
            alt=""
          />
        </v-btn>
      </v-col>
      <v-col>
        <v-btn @click="dummy()">Dummy</v-btn>
      </v-col>
    </v-row>
    <v-col cols="12">
      <v-card>
        <v-data-table
          :headers="headers"
          :items="filteredInvoices"
          :loading="
            isLoading?.action === 'fetchInvoices' ||
            (isLoading === null && invoices.length === 0)
          "
        >
          <template v-slot:loading>
            <v-skeleton-loader type="table-row@10"></v-skeleton-loader>
          </template>
          <template #item.subtotal="{ value }">
            {{ value.toFixed(2) }} €
          </template>
          <template #item.status="{ value }">
            <v-chip
              size="small"
              :color="status_colors[value as keyof typeof status_colors]"
              variant="flat"
            >
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
                  :disabled="item.customer.email === ''"
                  :loading="
                    isLoading?.action === 'sendInvoice' &&
                    isLoading?.id === item.id
                  "
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
                  :loading="
                    isLoading?.action === 'markInvoicePaid' &&
                    isLoading?.id === item.id
                  "
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
                  :loading="
                    isLoading?.action === 'purchaseInternetmarke' &&
                    isLoading?.id === item.id
                  "
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
                  :loading="
                    isLoading?.action === 'printInternetmarke' &&
                    isLoading?.id === item.invoiceNumber
                  "
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
                  :loading="
                    isLoading?.action === 'printInvoice' &&
                    isLoading?.id === item.id
                  "
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
import { onMounted, computed, ref } from "vue";

const appStore = useAppStore();
const { isLoading, invoices } = storeToRefs(appStore);
const {
  printInternetmarke,
  purchaseInternetmarke,
  markInvoicePaid,
  fetchInvoices,
  printInvoice,
  sendInvoice,
  updatePayments,
  dummy
} = appStore;

const status_colors = {
  complete: "#ff7d5d",
  draft: "#242933",
  sent: "#28ebff",
  paid: "#62efbd",
  voided: "#1c212b",
} as const;

const selectedStates = ref(["draft", "sent", "paid"]);

const filteredInvoices = computed(() => {
  return invoices.value.filter((item) =>
    selectedStates.value.includes(item.status),
  );
});

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
  },
] as const;

onMounted(() => {
  fetchInvoices();
});
</script>
