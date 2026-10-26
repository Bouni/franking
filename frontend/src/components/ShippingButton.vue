<script setup lang="ts">
import { storeToRefs } from "pinia";
import { computed } from "vue";
import dhlIcon from "@/assets/DHL.svg";
import postIcon from "@/assets/Post.svg";
import { useAppStore } from "@/store/app";

const props = defineProps<{
  invoiceId: string;
  countryCode: string;
  disabled?: boolean;
}>();

// Internetmarke (Deutsche Post) within Germany, DHL Warenpost International otherwise
const national = computed(() => props.countryCode?.toUpperCase() === "DE");

const store = useAppStore();
const { isLoading } = storeToRefs(store);
const { createLabel } = store;
</script>

<template>
  <v-tooltip
    location="top"
    :text="
      national
        ? 'Purchase Internetmarke (Deutsche Post)'
        : 'Purchase DHL Warenpost International Premium'
    "
  >
    <template #activator="{ props: tooltipProps }">
      <v-btn
        v-bind="tooltipProps"
        class="ma-2"
        color="#ffcc00"
        :disabled="disabled"
        icon
        :loading="
          isLoading?.action === 'createLabel' && isLoading?.id === invoiceId
        "
        @click="createLabel(invoiceId)"
      >
        <v-img
          :alt="national ? 'Deutsche Post' : 'DHL'"
          :src="national ? postIcon : dhlIcon"
          :width="national ? 28 : 34"
        />
      </v-btn>
    </template>
  </v-tooltip>
</template>
