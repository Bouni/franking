<template>
  <v-row>
    <v-row align="center" class="mb-4">
      <v-col class="d-flex justify-center justify-md-start" cols="12" md="auto">
        <Internetmarke />
      </v-col>

      <v-col
        v-for="(color, state) in status_colors"
        :key="state"
        cols="6"
        md="auto"
        sm="4"
      >
        <v-switch
          v-model="selectedStates"
          :color="color"
          hide-details
          :label="state"
          :value="state"
        />
      </v-col>

      <v-col class="d-flex justify-center ml-md-4" cols="12" md="auto">
        <v-btn
          class="px-4 mt-3 ml-5"
          color="primary"
          :loading="isLoading?.action === 'updatePayments'"
          @click="updatePayments()"
        >
          <img
            alt=""
            class="mr-2"
            height="20"
            :src="sparkasseIcon"
            width="20"
          />

          <span class="mx-1">Update</span>

          <img alt="" class="ml-2" height="20" :src="paypalIcon" width="20" />
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
          :mobile-breakpoint="600"
        >
          <template #loading>
            <v-skeleton-loader type="table-row@10" />
          </template>

          <template #item.subtotal="{ value }">
            {{ value.toFixed(2) }} €
          </template>

          <template #item.status="{ item }">
            <v-chip
              :color="status_colors[item.status as keyof typeof status_colors]"
              size="small"
              variant="flat"
            >
              {{ item.status }}
              <template #append>
                <v-img
                  v-if="getPaymentMethod(item)"
                  class="ml-2"
                  :src="
                    getPaymentMethod(item) == 'PayPal'
                      ? paypalIcon
                      : sparkasseIcon
                  "
                  width="16"
                />
              </template>
            </v-chip>
          </template>

          <template #item.items="{ item }">
            <v-menu
              :close-on-content-click="false"
              location="end"
              open-on-hover
            >
              <template #activator="{ props: menuProps }">
                <v-btn
                  v-bind="menuProps"
                  prepend-icon="mdi-format-list-bulleted"
                  size="small"
                  variant="tonal"
                >
                  {{ item.items.length }}
                </v-btn>
              </template>

              <v-card :title="`Items ${item.invoiceNumber}`">
                <v-table density="compact">
                  <thead>
                    <tr>
                      <th class="text-end">Qty</th>
                      <th>Description</th>
                      <th class="text-end">Unit price</th>
                      <th class="text-end">Total</th>
                    </tr>
                  </thead>

                  <tbody>
                    <tr v-for="i in item.items" :key="i.id">
                      <td class="text-end">{{ i.quantity }}</td>
                      <td>{{ i.description }}</td>

                      <td class="text-end">
                        {{ formatPrice(i.unitPrice) }}
                      </td>

                      <td class="text-end">
                        {{ formatPrice(i.lineTotal) }}
                      </td>
                    </tr>
                  </tbody>
                </v-table>
              </v-card>
            </v-menu>
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
            />
          </template>

          <template #item.customer.email="{ value }">
            <a v-if="value" :href="`mailto:${value}`">{{ value }}</a>
          </template>

          <template #item.customer.countryCode="{ value }">
            <span class="ms-2">{{ value }}</span>

            <span
              class="ml-4"
              :class="`fi fi-${value.toLowerCase()}`"
              style="border-radius: 2px"
            />
          </template>

          <template #item.actions="{ item }">
            <ActionButton
              action="sendInvoice"
              :action-id="item.id"
              color="lime-accent-3"
              :disabled="item.customer.email === ''"
              icon="mdi-email-fast"
              tooltip="Send invoice as e-mail"
              @click="sendInvoice(item.id)"
            />

            <SpeedDialButton
              :action-id="item.id"
              :actions="[
                {
                  icon: paypalIcon,
                  color: 'grey-darken-3',
                  action: 'markInvoicePaid',
                  onClick: () => markInvoicePaid(item.id, 'PayPal'),
                },
                {
                  icon: sparkasseIcon,
                  color: 'grey-darken-3',
                  action: 'markInvoicePaid',
                  onClick: () => markInvoicePaid(item.id, 'Bank transfer'),
                },
              ]"
              :disabled="item.status !== 'sent'"
            />
            <!-- <ActionButton -->
            <!--   icon="mdi-currency-eur" -->
            <!--   color="green" -->
            <!--   tooltip="Mark as paid" -->
            <!--   action="markInvoicePaid" -->
            <!--   :action-id="item.id" -->
            <!--   :disabled="item.status !== 'sent'" -->
            <!--   @click="markInvoicePaid(item.id)" -->
            <!-- /> -->

            <ShippingButton
              :country-code="item.customer.countryCode"
              :disabled="!!item.label"
              :invoice-id="item.id"
            />

            <ActionButton
              action="printLabel"
              :action-id="item.invoiceNumber"
              color="purple"
              :disabled="!item.label"
              icon="mdi-printer"
              :tooltip="
                item.label
                  ? `Print shipping label (${printerNames[item.label.printer] ?? item.label.printer})`
                  : 'Print shipping label'
              "
              @click="printLabel(item.invoiceNumber)"
            />

            <ActionButton
              action="cancelLabel"
              :action-id="item.invoiceNumber"
              color="red-darken-2"
              :disabled="!item.label || item.label.carrier === 'internetmarke'"
              icon="mdi-cancel"
              tooltip="Cancel shipping label"
              @click="confirmCancelLabel(item.invoiceNumber)"
            />

            <v-btn
              v-if="item.label?.tracking_url"
              :href="item.label.tracking_url"
              icon="mdi-truck-fast"
              size="small"
              target="_blank"
              variant="text"
            />

            <ActionButton
              action="printInvoice"
              :action-id="item.id"
              color="red"
              :disabled="item.status !== 'paid'"
              icon="mdi-printer-outline"
              tooltip="Print invoice"
              @click="printInvoice(item.id)"
            />

            <ActionButton
              action="markInvoiceComplete"
              :action-id="item.id"
              color="lime-accent-3"
              :disabled="item.status !== 'paid'"
              icon="mdi-check"
              tooltip="Mark as complete"
              @click="markInvoiceComplete(item.id)"
            />
          </template>
        </v-data-table>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";
import paypalIcon from "@/assets/PayPal.svg";
import sparkasseIcon from "@/assets/Sparkasse.svg";
import ActionButton from "@/components/ActionButton.vue";
import Internetmarke from "@/components/Internetmarke.vue";
import ShippingButton from "@/components/ShippingButton.vue";
import SpeedDialButton from "@/components/SpeedDialButton.vue";
import { useAppStore } from "@/store/app";

const appStore = useAppStore();
const { isLoading, invoices } = storeToRefs(appStore);
const {
  printLabel,
  cancelLabel,
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

const printerNames: Record<string, string> = {
  ql710: "QL-710W",
  ql1110: "QL-1110NWB",
};

function confirmCancelLabel(invoice_number: string) {
  if (window.confirm(`Cancel the shipping label for ${invoice_number}?`)) {
    cancelLabel(invoice_number);
  }
}

const selectedStates = ref(["draft", "sent", "paid"]);

const statusCounts = computed(() => {
  const counts = Object.keys(status_colors).reduce(
    (acc, status) => {
      acc[status] = 0;
      return acc;
    },
    {} as Record<string, number>,
  );

  for (const item of invoices.value) {
    if (item.status in counts) {
      counts[item.status]++;
    }
  }

  return counts;
});

const filteredInvoices = computed(() => {
  return invoices.value.filter((item) =>
    selectedStates.value.includes(item.status),
  );
});

// Same format as the Sum column
function formatPrice(value: number) {
  return `${(value ?? 0).toFixed(2)} €`;
}

function getPaymentMethod(item: any) {
  return item.statusHistory.find((entry: any) => entry.paymentMethod)
    ?.paymentMethod;
}

const headers = [
  { title: "Invoice number", key: "invoiceNumber", align: "start" },
  { title: "Shipping", key: "checks", align: "center", sortable: false },
  { title: "Status", key: "status", align: "center", sortable: false },
  { title: "Sum", key: "subtotal", align: "start" },
  { title: "Items", key: "items", align: "center", sortable: false },
  { title: "Customer", key: "customer.name", align: "start" },
  { title: "Contact", key: "customer.contactName", align: "start" },
  { title: "Email", key: "customer.email", align: "start" },
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
