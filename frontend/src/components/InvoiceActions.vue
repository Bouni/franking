<script setup lang="ts">
import paypalIcon from "@/assets/PayPal.svg";
import sparkasseIcon from "@/assets/Sparkasse.svg";
import ActionButton from "@/components/ActionButton.vue";
import ShippingButton from "@/components/ShippingButton.vue";
import SpeedDialButton from "@/components/SpeedDialButton.vue";
import { printerNames } from "@/invoice";
import { useAppStore } from "@/store/app";

defineProps<{
  invoice: any;
  // Narrow screens: the groups wrap instead of overflowing
  compact?: boolean;
}>();

// The send dialog lives in the invoice list
const emit = defineEmits(["send"]);

const {
  printLabel,
  cancelLabel,
  markInvoicePaid,
  markInvoiceComplete,
  printInvoice,
} = useAppStore();

function confirmCancelLabel(invoice_number: string) {
  if (window.confirm(`Cancel the shipping label for ${invoice_number}?`)) {
    cancelLabel(invoice_number);
  }
}
</script>

<template>
  <div class="actions" :class="{ compact }">
    <!-- Invoice -->
    <div class="action-group">
      <ActionButton
        action="sendInvoice"
        :action-id="invoice.id"
        color="#1982c4"
        :disabled="!invoice.customer.email"
        icon="mdi-email-fast"
        tooltip="Send invoice as e-mail"
        @click="emit('send', invoice)"
      />

      <ActionButton
        action="printInvoice"
        :action-id="invoice.id"
        color="#1982c4"
        :disabled="invoice.status !== 'paid'"
        icon="mdi-printer-outline"
        tooltip="Print invoice"
        @click="printInvoice(invoice.id)"
      />
    </div>

    <v-divider v-if="!compact" vertical />

    <!-- Payment -->
    <div class="action-group">
      <SpeedDialButton
        :action-id="invoice.id"
        :actions="[
          {
            icon: paypalIcon,
            color: 'white',
            action: 'markInvoicePaid',
            onClick: () => markInvoicePaid(invoice.id, 'PayPal'),
          },
          {
            icon: sparkasseIcon,
            color: 'white',
            action: 'markInvoicePaid',
            onClick: () => markInvoicePaid(invoice.id, 'Bank transfer'),
          },
        ]"
        color="#8ac926"
        :disabled="invoice.status !== 'sent'"
      />
    </div>

    <v-divider v-if="!compact" vertical />

    <!-- Shipping -->
    <div class="action-group">
      <ShippingButton
        :country-code="invoice.customer.countryCode"
        :disabled="!!invoice.label || invoice.status !== 'paid'"
        :invoice-id="invoice.id"
      />

      <ActionButton
        action="printLabel"
        :action-id="invoice.invoiceNumber"
        color="#ff924c"
        :disabled="!invoice.label"
        icon="mdi-printer"
        :tooltip="
          invoice.label
            ? `Print shipping label (${printerNames[invoice.label.printer] ?? invoice.label.printer})`
            : 'Print shipping label'
        "
        @click="printLabel(invoice.invoiceNumber)"
      />

      <ActionButton
        action="cancelLabel"
        :action-id="invoice.invoiceNumber"
        color="#e63946"
        :disabled="!invoice.label || invoice.label.carrier === 'internetmarke'"
        icon="mdi-cancel"
        tooltip="Cancel shipping label"
        @click="confirmCancelLabel(invoice.invoiceNumber)"
      />

      <v-tooltip location="top" text="Track shipment">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="tooltipProps"
            class="ma-1"
            :color="invoice.label?.tracking_url ? '#00918e' : undefined"
            :disabled="!invoice.label?.tracking_url"
            :href="invoice.label?.tracking_url"
            icon="mdi-truck-fast"
            target="_blank"
            :variant="invoice.label?.tracking_url ? 'flat' : 'tonal'"
          />
        </template>
      </v-tooltip>
    </div>

    <v-divider v-if="!compact" vertical />

    <!-- Done -->
    <div class="action-group">
      <ActionButton
        action="markInvoiceComplete"
        :action-id="invoice.id"
        color="#7209b7"
        :disabled="invoice.status !== 'paid'"
        icon="mdi-check"
        tooltip="Mark as complete"
        @click="markInvoiceComplete(invoice.id)"
      />
    </div>
  </div>
</template>

<style scoped>
.actions {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.actions.compact {
  flex-wrap: wrap;
  justify-content: flex-start;
  gap: 0 4px;
}

.action-group {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
}

.actions .v-divider {
  align-self: stretch;
  margin-block: 12px;
}
</style>
