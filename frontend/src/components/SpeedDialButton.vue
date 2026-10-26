<script setup lang="ts">
import { storeToRefs } from "pinia";
import { mergeProps } from "vue";
import { type LoadingState, useAppStore } from "@/store/app";

interface DialAction {
  icon: string; // The imported path (e.g., /src/assets/paypal.svg)
  color: string;
  action: LoadingState["action"];
  onClick: () => void;
}

defineProps<{
  actionId: string | number;
  actions: DialAction[];
  disabled?: boolean;
}>();

const store = useAppStore();
const { isLoading } = storeToRefs(store);
</script>

<template>
  <v-speed-dial location="top center" transition="scale-transition">
    <template #activator="{ props: dialProps }">
      <v-tooltip location="top" text="Mark Invoice as paid">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="mergeProps(dialProps, tooltipProps)"
            color="green"
            :disabled="disabled"
            icon="mdi-currency-eur"
          />
        </template>
      </v-tooltip>
    </template>

    <v-btn
      v-for="item in actions"
      :key="item.action"
      class="ma-2"
      :color="item.color"
      icon
      :loading="isLoading?.action === item.action && isLoading?.id === actionId"
      size="large"
      @click="item.onClick"
    >
      <v-img height="20" :src="item.icon" width="20" />
    </v-btn>
  </v-speed-dial>
</template>
