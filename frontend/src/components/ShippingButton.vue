<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";
import dhlIcon from "@/assets/DHL.svg";
import { useAppStore } from "@/store/app";

const props = defineProps<{
  invoiceId: string;
  countryCode: string;
  disabled?: boolean;
}>();

// DHL Kleinpaket within Germany, DHL Warenpost International Premium otherwise
const national = computed(() => props.countryCode?.toUpperCase() === "DE");

// No DHL product via Sendcloud for these countries, the label is bought manually
const MANUAL_COUNTRIES = new Set(["US"]);
const manual = computed(() =>
  MANUAL_COUNTRIES.has(props.countryCode?.toUpperCase()),
);
const manualDialog = ref(false);

function purchase() {
  if (manual.value) {
    manualDialog.value = true;
  } else {
    createLabel(props.invoiceId);
  }
}

const store = useAppStore();
const { isLoading } = storeToRefs(store);
const { createLabel } = store;
</script>

<template>
  <v-tooltip
    location="top"
    :text="
      manual
        ? 'DHL Paket 2kg, buy the label manually'
        : national
          ? 'Purchase DHL Kleinpaket'
          : 'Purchase DHL Warenpost International Premium'
    "
  >
    <template #activator="{ props: tooltipProps }">
      <v-btn
        v-bind="tooltipProps"
        class="ma-1 dhl-button"
        color="#ffcc00"
        :disabled="disabled"
        icon
        :loading="
          isLoading?.action === 'createLabel' && isLoading?.id === invoiceId
        "
        variant="flat"
        @click="purchase"
      >
        <v-img alt="DHL" :src="dhlIcon" width="34" />
      </v-btn>
    </template>
  </v-tooltip>

  <v-dialog v-model="manualDialog" max-width="520">
    <v-card prepend-icon="mdi-truck-alert" title="Manual shipping label">
      <v-card-text>
        <p>
          Sendcloud offers no DHL product for shipments to
          <strong>{{ countryCode?.toUpperCase() }}</strong
          >, so this label can't be bought here.
        </p>

        <p class="mt-3">
          Please purchase a DHL shipping label for a
          <strong>"2kg Paket"</strong> manually and attach it to the parcel. The
          customer was charged a fixed shipping price for this.
        </p>
      </v-card-text>

      <v-card-actions>
        <v-spacer />

        <v-btn color="primary" variant="flat" @click="manualDialog = false">
          Got it
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
/* Vuetify fades disabled buttons almost completely, keep the DHL button
   recognizable but clearly inactive: yellow and logo, desaturated */
.dhl-button.v-btn--disabled {
  background: #ffcc00 !important;
  filter: grayscale(0.85);
  opacity: 0.6;
}
</style>
