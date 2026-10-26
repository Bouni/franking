prepend-icon="mdi-cash0
<template>
  <v-row>
    <v-col cols="12">
      <v-chip color="#ffcc00" size="large" variant="flat">
        {{ (internetmarke.balance / 100).toFixed(2) }} €
        <template #prepend>
          <v-img class="mr-2" :src="postIcon" width="32" />
        </template>
      </v-chip>
    </v-col>
  </v-row>
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
