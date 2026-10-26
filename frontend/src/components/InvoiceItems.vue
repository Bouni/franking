<script setup lang="ts">
import { formatPrice } from "@/invoice";

defineProps<{
  invoice: any;
}>();
</script>

<template>
  <v-table class="invoice-items" density="compact">
    <thead>
      <tr>
        <th class="text-end">Qty</th>
        <th>Item</th>
        <th class="text-end">Unit</th>
        <th class="text-end">Total</th>
      </tr>
    </thead>

    <tbody>
      <tr
        v-for="i in invoice.items"
        :key="i.id"
        :class="{ 'text-medium-emphasis': !i.productId }"
      >
        <td class="text-end text-no-wrap">{{ i.quantity }} ×</td>
        <td>{{ i.description }}</td>

        <td class="text-end text-no-wrap amount">
          {{ formatPrice(i.unitPrice) }}
        </td>

        <td class="text-end text-no-wrap amount">
          {{ formatPrice(i.lineTotal) }}
        </td>
      </tr>
    </tbody>

    <tfoot>
      <tr>
        <td class="font-weight-bold" colspan="3">Sum</td>

        <td class="text-end text-no-wrap amount font-weight-bold">
          {{ formatPrice(invoice.subtotal) }}
        </td>
      </tr>
    </tfoot>
  </v-table>
</template>

<style scoped>
.invoice-items {
  background: transparent;
}

.invoice-items th {
  font-weight: 600 !important;
}

.invoice-items .amount {
  font-variant-numeric: tabular-nums;
}

.invoice-items tfoot td {
  border-top: 2px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
