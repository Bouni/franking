<script setup lang="ts">
import { ref } from "vue";
import paypalIcon from "@/assets/PayPal.svg";
import sparkasseIcon from "@/assets/Sparkasse.svg";
import InvoiceActions from "@/components/InvoiceActions.vue";
import InvoiceItems from "@/components/InvoiceItems.vue";
import {
  formatDate,
  formatPrice,
  hasShipping,
  paymentMethod,
  statusColor,
} from "@/invoice";

defineProps<{
  invoice: any;
}>();

const emit = defineEmits(["send"]);

const showItems = ref(false);
</script>

<template>
  <v-card
    class="invoice-card h-100 d-flex flex-column"
    :style="{ '--status-color': statusColor(invoice.status) }"
    variant="flat"
  >
    <v-card-item>
      <v-card-title class="d-flex align-center ga-2">
        <span class="text-truncate">{{ invoice.invoiceNumber }}</span>
      </v-card-title>

      <v-card-subtitle>{{ formatDate(invoice.issueDate) }}</v-card-subtitle>

      <template #append>
        <v-chip
          :color="statusColor(invoice.status)"
          size="small"
          variant="flat"
        >
          {{ invoice.status }}
          <template v-if="paymentMethod(invoice)" #append>
            <v-img
              class="ml-2"
              :src="
                paymentMethod(invoice) === 'PayPal' ? paypalIcon : sparkasseIcon
              "
              width="16"
            />
          </template>
        </v-chip>
      </template>
    </v-card-item>

    <v-card-text class="pb-2">
      <div class="d-flex align-start ga-3">
        <div class="flex-grow-1 min-width-0">
          <div class="text-body-1 font-weight-medium text-truncate">
            {{ invoice.customer?.name }}
          </div>

          <div
            v-if="
              invoice.customer?.contactName &&
              invoice.customer.contactName !== invoice.customer.name
            "
            class="text-truncate"
          >
            {{ invoice.customer.contactName }}
          </div>

          <div class="d-flex align-center ga-2 mt-1">
            <span
              v-if="invoice.customer?.countryCode"
              class="flag"
              :class="`fi fi-${invoice.customer.countryCode.toLowerCase()}`"
            />

            <span class="text-truncate">
              {{ invoice.customer?.postalCode }} {{ invoice.customer?.city }}
            </span>
          </div>

          <a
            v-if="invoice.customer?.email"
            class="d-block text-truncate mt-1"
            :href="`mailto:${invoice.customer.email}`"
          >
            {{ invoice.customer.email }}
          </a>
        </div>

        <div class="text-end">
          <div class="text-h6 amount text-no-wrap">
            {{ formatPrice(invoice.subtotal) }}
          </div>

          <v-tooltip
            v-if="!hasShipping(invoice)"
            location="top"
            text="No shipping costs on this invoice"
          >
            <template #activator="{ props: tooltipProps }">
              <v-chip
                v-bind="tooltipProps"
                class="mt-1"
                color="warning"
                prepend-icon="mdi-alert"
                size="x-small"
                variant="tonal"
              >
                No shipping
              </v-chip>
            </template>
          </v-tooltip>
        </div>
      </div>

      <v-btn
        :append-icon="showItems ? 'mdi-chevron-up' : 'mdi-chevron-down'"
        class="mt-2 px-1"
        prepend-icon="mdi-format-list-bulleted"
        size="small"
        variant="text"
        @click="showItems = !showItems"
      >
        {{ invoice.items.length }}
        {{ invoice.items.length === 1 ? "item" : "items" }}
      </v-btn>

      <v-expand-transition>
        <div v-show="showItems" class="items-wrapper">
          <InvoiceItems :invoice="invoice" />
        </div>
      </v-expand-transition>
    </v-card-text>

    <v-spacer />
    <v-divider />

    <v-card-actions class="px-2">
      <InvoiceActions
        compact
        :invoice="invoice"
        @send="emit('send', invoice)"
      />
    </v-card-actions>
  </v-card>
</template>

<style scoped>
.invoice-card {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-left: 5px solid var(--status-color);
}

.min-width-0 {
  min-width: 0;
}

.flag {
  border-radius: 2px;
  flex-shrink: 0;
}

.amount {
  font-variant-numeric: tabular-nums;
}

/* Long item descriptions scroll sideways instead of widening the card */
.items-wrapper {
  overflow-x: auto;
  margin-inline: -16px;
}
</style>
