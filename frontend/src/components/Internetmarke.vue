<template>
  <v-tooltip location="bottom" text="Internetmarke balance">
    <template #activator="{ props: tooltipProps }">
      <v-chip v-bind="tooltipProps" color="#ffcc00" size="large" variant="flat">
        {{ (internetmarke.balance / 100).toFixed(2) }} €
        <template #prepend>
          <v-img class="mr-2" :src="postIcon" width="32" />
        </template>
      </v-chip>
    </template>
  </v-tooltip>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { onMounted } from "vue";
import postIcon from "@/assets/Post.svg";
import { useAppStore } from "@/store/app";

const appStore = useAppStore();
const { internetmarke } = storeToRefs(appStore);
const { fetchBalance } = appStore;

onMounted(() => {
  fetchBalance();
});
</script>
