<template>
  <div>
    <v-card class="mb-4" variant="flat">
      <v-card-text class="d-flex flex-wrap align-center ga-3">
        <Internetmarke />

        <v-btn
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

          <span class="mx-1">Update payments</span>
          <img alt="" class="ml-2" height="20" :src="paypalIcon" width="20" />
        </v-btn>

        <v-spacer />

        <v-text-field
          v-model="search"
          class="search"
          clearable
          density="compact"
          flat
          hide-details
          placeholder="Invoice, customer, email, city"
          prepend-inner-icon="mdi-magnify"
          variant="solo-filled"
        />
      </v-card-text>

      <v-card-text class="pt-0">
        <!-- Each chip filters by its status and shows how many invoices have it -->
        <v-chip-group
          v-model="selectedStates"
          class="status-filter"
          column
          multiple
        >
          <v-chip
            v-for="(color, status) in statusColors"
            :key="status"
            :class="{ selected: selectedStates.includes(status) }"
            :color="selectedStates.includes(status) ? color : undefined"
            :value="status"
            :variant="selectedStates.includes(status) ? 'flat' : 'outlined'"
          >
            <template #prepend>
              <v-icon
                v-if="selectedStates.includes(status)"
                class="mr-1"
                icon="mdi-check"
                size="small"
              />

              <span v-else class="dot mr-2" :style="{ background: color }" />
            </template>

            <span class="text-capitalize">{{ status }}</span>
            <span class="count ml-2">{{ statusCounts[status] }}</span>
          </v-chip>
        </v-chip-group>
      </v-card-text>
    </v-card>

    <!-- Large screens: table -->
    <v-card v-if="lgAndUp" variant="flat">
      <v-data-table
        :headers="headers"
        hover
        :items="filteredInvoices"
        :loading="loading"
      >
        <template #loading>
          <v-skeleton-loader type="table-row@10" />
        </template>

        <template #item.invoiceNumber="{ item }">
          <div class="font-weight-medium text-no-wrap">
            {{ item.invoiceNumber }}
          </div>

          <div class="text-caption text-medium-emphasis">
            {{ formatDate(item.issueDate) }}
          </div>
        </template>

        <template #item.customer.name="{ item }">
          <div class="py-2 cell-customer">
            <div class="font-weight-medium">{{ item.customer?.name }}</div>

            <div
              v-if="
                item.customer?.contactName &&
                item.customer.contactName !== item.customer.name
              "
              class="text-medium-emphasis"
            >
              {{ item.customer.contactName }}
            </div>

            <a
              v-if="item.customer?.email"
              class="text-caption"
              :href="`mailto:${item.customer.email}`"
            >
              {{ item.customer.email }}
            </a>
          </div>
        </template>

        <template #item.customer.city="{ item }">
          <div class="py-2">
            <div>{{ item.customer?.address }}</div>

            <div class="d-flex align-center ga-2">
              <span
                v-if="item.customer?.countryCode"
                class="flag"
                :class="`fi fi-${item.customer.countryCode.toLowerCase()}`"
              />

              <span>
                {{ item.customer?.postalCode }} {{ item.customer?.city }}
              </span>
            </div>
          </div>
        </template>

        <template #item.status="{ item }">
          <v-chip :color="statusColor(item.status)" size="small" variant="flat">
            {{ item.status }}
            <template v-if="paymentMethod(item)" #append>
              <v-img
                class="ml-2"
                :src="
                  paymentMethod(item) === 'PayPal' ? paypalIcon : sparkasseIcon
                "
                width="16"
              />
            </template>
          </v-chip>
        </template>

        <template #item.subtotal="{ value }">
          <span class="amount text-no-wrap">{{ formatPrice(value) }}</span>
        </template>

        <template #item.items="{ item }">
          <div class="cell-items py-2">
            <div
              v-for="i in item.items"
              :key="i.id"
              class="item-line"
              :class="{ 'text-medium-emphasis': !i.productId }"
            >
              <span class="text-no-wrap">{{ i.quantity }} ×</span>
              <span class="item-description">{{ i.description }}</span>

              <span class="amount text-no-wrap">
                {{ formatPrice(i.lineTotal) }}
              </span>
            </div>

            <v-chip
              v-if="!hasShipping(item)"
              class="mt-1"
              color="warning"
              prepend-icon="mdi-alert"
              size="x-small"
              variant="tonal"
            >
              No shipping
            </v-chip>
          </div>
        </template>

        <template #item.actions="{ item }">
          <InvoiceActions :invoice="item" @send="requestSendInvoice" />
        </template>
      </v-data-table>
    </v-card>

    <!-- Phones and tablets: cards -->
    <v-data-iterator
      v-else
      v-model:page="page"
      :items="filteredInvoices"
      :items-per-page="12"
      :loading="loading"
    >
      <template #loader>
        <v-row dense>
          <v-col v-for="n in 4" :key="n" cols="12">
            <v-skeleton-loader type="article, actions" />
          </v-col>
        </v-row>
      </template>

      <template #no-data>
        <v-card class="pa-8 text-center text-medium-emphasis" variant="flat">
          No invoices found
        </v-card>
      </template>

      <template #default="{ items }">
        <v-row dense>
          <v-col v-for="{ raw } in items" :key="raw.id" cols="12">
            <InvoiceCard :invoice="raw" @send="requestSendInvoice" />
          </v-col>
        </v-row>
      </template>

      <template #footer="{ pageCount }">
        <v-pagination
          v-if="pageCount > 1"
          v-model="page"
          class="mt-4"
          density="comfortable"
          :length="pageCount"
          :total-visible="xs ? 5 : 7"
        />
      </template>
    </v-data-iterator>

    <v-dialog v-model="sendDialog" :fullscreen="xs" max-width="760">
      <v-card
        :prepend-icon="isResend ? 'mdi-email-sync' : 'mdi-email-fast'"
        :subtitle="`To ${email.recipient ?? sendInvoiceItem?.customer?.email}`"
        :title="`${isResend ? 'Send invoice again' : 'Send invoice'} ${sendInvoiceItem?.invoiceNumber ?? ''}`"
      >
        <v-card-text>
          <v-alert
            v-if="isResend"
            class="mb-4"
            density="compact"
            type="warning"
            variant="tonal"
          >
            This invoice has already been sent, its current status is
            <strong>{{ sendInvoiceItem?.status }}</strong
            >.
          </v-alert>

          <v-text-field v-model="email.subject" label="Subject" />

          <v-textarea
            v-model="email.body"
            auto-grow
            label="Text"
            max-rows="20"
            rows="12"
          />

          <div class="text-caption">
            Changes here only apply to this email, the template is edited in the
            Settings tab.
          </div>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn @click="sendDialog = false">Cancel</v-btn>

          <v-btn
            color="#1982c4"
            :disabled="!email.subject.trim() || !email.body.trim()"
            prepend-icon="mdi-send"
            variant="flat"
            @click="confirmSend"
          >
            {{ isResend ? "Send again" : "Send" }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useDisplay } from "vuetify";
import paypalIcon from "@/assets/PayPal.svg";
import sparkasseIcon from "@/assets/Sparkasse.svg";
import Internetmarke from "@/components/Internetmarke.vue";
import InvoiceActions from "@/components/InvoiceActions.vue";
import InvoiceCard from "@/components/InvoiceCard.vue";
import {
  formatDate,
  formatPrice,
  hasShipping,
  paymentMethod,
  statusColor,
  statusColors,
} from "@/invoice";
import { type InvoiceEmail, useAppStore } from "@/store/app";

const appStore = useAppStore();
const { isLoading, invoices } = storeToRefs(appStore);
const {
  fetchInvoices,
  previewInvoiceEmail,
  sendInvoice,
  startPaymentWatch,
  stopPaymentWatch,
  updatePayments,
} = appStore;

// The table needs the width of a large screen, smaller ones get cards
const { lgAndUp, xs } = useDisplay();

const loading = computed(
  () =>
    isLoading.value?.action === "fetchInvoices" ||
    (isLoading.value === null && invoices.value.length === 0),
);

// Show the email before sending, so subject and text can be adjusted, and
// warn when the invoice already went out
const sendDialog = ref(false);
const sendInvoiceItem = ref<any>(null);
const email = ref<InvoiceEmail>({ subject: "", body: "" });
const isResend = computed(
  () => !!sendInvoiceItem.value && sendInvoiceItem.value.status !== "draft",
);

async function requestSendInvoice(invoice: any) {
  const preview = await previewInvoiceEmail(invoice.id);
  if (!preview) {
    return;
  }
  sendInvoiceItem.value = invoice;
  email.value = preview;
  sendDialog.value = true;
}

function confirmSend() {
  sendDialog.value = false;
  if (sendInvoiceItem.value) {
    sendInvoice(sendInvoiceItem.value.id, email.value);
  }
}

const selectedStates = ref<string[]>(["draft", "sent", "paid"]);
const search = ref<string | null>("");
const page = ref(1);

const statusCounts = computed(() => {
  const counts = Object.fromEntries(
    Object.keys(statusColors).map((status) => [status, 0]),
  );
  for (const item of invoices.value) {
    if (item.status in counts) {
      counts[item.status]++;
    }
  }
  return counts;
});

const filteredInvoices = computed(() => {
  const term = (search.value ?? "").trim().toLowerCase();
  return invoices.value.filter(
    (item) =>
      selectedStates.value.includes(item.status) &&
      (!term ||
        [
          item.invoiceNumber,
          item.customer?.name,
          item.customer?.contactName,
          item.customer?.email,
          item.customer?.city,
        ].some((value) => value?.toLowerCase().includes(term))),
  );
});

// A changed filter starts again on the first page of cards
watch([selectedStates, search], () => {
  page.value = 1;
});

const headers = [
  { title: "Invoice", key: "invoiceNumber", align: "start" },
  { title: "Customer", key: "customer.name", align: "start" },
  { title: "Address", key: "customer.city", align: "start" },
  { title: "Status", key: "status", align: "center" },
  { title: "Sum", key: "subtotal", align: "end" },
  { title: "Items", key: "items", align: "start", sortable: false },
  { title: "Actions", key: "actions", align: "center", sortable: false },
] as const;

onMounted(() => {
  fetchInvoices();
  startPaymentWatch();
});

onUnmounted(stopPaymentWatch);
</script>

<style scoped>
.search {
  flex: 1 1 260px;
  max-width: 360px;
}

.status-filter .v-chip {
  font-weight: 500;
}

.status-filter .v-chip:not(.selected) {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  border-color: rgba(var(--v-border-color), 0.25);
}

.status-filter .dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.status-filter .count {
  min-width: 22px;
  padding: 0 6px;
  border-radius: 10px;
  font-size: 0.75rem;
  font-weight: 700;
  line-height: 20px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  background: rgba(var(--v-theme-on-surface), 0.08);
}

/* On a colored chip a darkened pill works for light and dark status colors */
.status-filter .selected .count {
  background: rgba(0, 0, 0, 0.18);
}

.cell-items {
  min-width: 260px;
  max-width: 380px;
  font-size: 0.875rem;
}

.item-line {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 8px;
  line-height: 1.4;
}

.item-description {
  overflow-wrap: anywhere;
}

.cell-customer {
  max-width: 260px;
}

.flag {
  border-radius: 2px;
  flex-shrink: 0;
}

.amount {
  font-variant-numeric: tabular-nums;
}
</style>
