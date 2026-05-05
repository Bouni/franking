<script setup lang="ts">
import { storeToRefs } from "pinia";
import { useAppStore, type LoadingState } from "@/store/app";
import { mergeProps } from "vue";

interface DialAction {
  icon: string; // The imported path (e.g., /src/assets/paypal.svg)
  color: string;
  action: LoadingState["action"];
  onClick: () => void;
}

const props = defineProps<{
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
      <v-tooltip text="Mark Invoice as paid" location="left">
        <template #activator="{ props: tooltipProps }">
          <v-btn
            v-bind="mergeProps(dialProps, tooltipProps)"
            color="green"
            icon="mdi-currency-eur"
            :disabled="disabled"
          >
          </v-btn>
        </template>
      </v-tooltip>
    </template>

    <v-btn
      icon
      v-for="item in actions"
      :key="item.action"
      :color="item.color"
      :loading="isLoading?.action === item.action && isLoading?.id === actionId"
      @click="item.onClick"
    >
      <v-img :src="item.icon" width="20" height="20" />
    </v-btn>
  </v-speed-dial>
</template>
