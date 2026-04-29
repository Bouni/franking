<template>
  <v-row>
    <v-row class="mb-4">
      <v-col cols="1">
        <Internetmarke />
      </v-col>
      <v-col v-for="(color, state) in status_colors" :key="state" cols="1">
        <v-switch
          v-model="selectedStates"
          :label="state"
          :value="state"
          :color="color"
          hide-details
        ></v-switch>
      </v-col>
      <v-col cols="1">
        <v-btn
          color="primary"
          class="px-4 mt-3 ml-5"
          :loading="isLoading?.action === 'updatePayments'"
          @click="updatePayments()"
        >
          <img
            :src="sparkasseIcon"
            width="20"
            height="20"
            class="mr-2"
            alt=""
          />
          <span class="mx-1">Update</span>
          <img :src="paypalIcon" width="20" height="20" class="ml-2" alt="" />
        </v-btn>
      </v-col>
    </v-row>

    <v-col cols="12">
      <v-card>
        <v-card-text class="d-flex flex-wrap ga-2">
          <v-chip
            v-for="(color, status) in status_colors"
            :key="status"
            :color="color"
            variant="flat"
          >
            <span class="text-capitalize">{{ status }}:</span>
            <span class="ml-2">{{ statusCounts[status] }}</span>
          </v-chip>
        </v-card-text>
      </v-card>
    </v-col>

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
          <template #item.status="{ item }">
            <v-chip
              size="small"
              :color="status_colors[item.status as keyof typeof status_colors]"
              variant="flat"
            >
              {{ item.status }}
              <template v-slot:append>
                <v-img
                  v-if="getPaymentMethod(item)"
                  width="16"
                  :src="
                    getPaymentMethod(item) == 'PayPal'
                      ? paypalIcon
                      : sparkasseIcon
                  "
                  class="ml-2"
                ></v-img>
              </template>
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
            <ActionButton
              icon="mdi-email-fast"
              color="lime-accent-3"
              tooltip="Send invoice as e-mail"
              action="sendInvoice"
              :action-id="item.id"
              :disabled="item.customer.email === ''"
              @click="sendInvoice(item.id)"
            />

            <ActionButton
              icon="mdi-currency-eur"
              color="green"
              tooltip="Mark as paid"
              action="markInvoicePaid"
              :action-id="item.id"
              :disabled="item.status !== 'sent'"
              @click="markInvoicePaid(item.id)"
            />

            <ActionButton
              icon="mdi-postage-stamp"
              color="blue-darken-1"
              tooltip="Purchase Internetmarke"
              action="purchaseInternetmarke"
              :action-id="item.id"
              :disabled="item.internetmarke"
              @click="purchaseInternetmarke(item.id)"
            />

            <ActionButton
              icon="mdi-printer"
              color="purple"
              tooltip="Print Internetmarke"
              action="printInternetmarke"
              :action-id="item.invoiceNumber"
              :disabled="!item.internetmarke"
              @click="printInternetmarke(item.invoiceNumber)"
            />

            <ActionButton
              icon="mdi-printer-outline"
              color="red"
              tooltip="Print invoice"
              action="printInvoice"
              :action-id="item.id"
              :disabled="item.status !== 'paid'"
              @click="printInvoice(item.id)"
            />

            <ActionButton
              icon="mdi-check"
              color="lime-accent-3"
              tooltip="Mark as complete"
              action="markInvoiceComplete"
              :action-id="item.id"
              :disabled="item.status !== 'paid'"
              @click="markInvoiceComplete(item.id)"
            />
          </template>
        </v-data-table>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import Internetmarke from "@/components/Internetmarke.vue";
import ActionButton from "@/components/ActionButton.vue";
import { useAppStore } from "@/store/app";
import { storeToRefs } from "pinia";
import { onMounted, computed, ref } from "vue";
import paypalIcon from "@/assets/PayPal.svg";
import sparkasseIcon from "@/assets/Sparkasse.svg";

const appStore = useAppStore();
const { isLoading, invoices } = storeToRefs(appStore);
const {
  printInternetmarke,
  purchaseInternetmarke,
  markInvoicePaid,
  markInvoiceComplete,
  fetchInvoices,
  printInvoice,
  sendInvoice,
  updatePayments,
} = appStore;

// colors from https://coolors.co/palette/ff595e-ffca3a-8ac926-1982c4-6a4c93

const status_colors = {
  complete: "#7209b7",
  draft: "#1982c4",
  sent: "#ffca3a",
  paid: "#8ac926",
  voided: "#8da9c4",
} as const;

const selectedStates = ref(["draft", "sent", "paid"]);

const statusCounts = computed(() => {
  const counts = Object.keys(status_colors).reduce(
    (acc, status) => {
      acc[status] = 0;
      return acc;
    },
    {} as Record<string, number>,
  );

  invoices.value.forEach((item) => {
    if (item.status in counts) {
      counts[item.status]++;
    }
  });

  return counts;
});

const filteredInvoices = computed(() => {
  return invoices.value.filter((item) =>
    selectedStates.value.includes(item.status),
  );
});

const getPaymentMethod = (item: any) => {
  return item.statusHistory.find((entry: any) => entry.paymentMethod)
    ?.paymentMethod;
};

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
