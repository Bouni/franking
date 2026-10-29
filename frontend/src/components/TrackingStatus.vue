<script setup lang="ts">
import { computed, ref } from "vue";
import { useDisplay } from "vuetify";
import { readable, trackingLook } from "@/invoice";
import api from "@/plugins/axios";

const props = defineProps<{
  label: any;
  invoiceNumber: string;
}>();

const { xs } = useDisplay();

// Latest Sendcloud tracking event, stored by the backend's tracking check
const tracking = computed(() => props.label?.tracking);
const look = computed(() =>
  trackingLook(tracking.value?.phase, tracking.value?.status_type),
);

function formatDateTime(value?: string) {
  return value
    ? new Date(value).toLocaleString("de-DE", {
        dateStyle: "short",
        timeStyle: "short",
      })
    : "";
}

function formatDate(value?: string) {
  return value ? new Date(value).toLocaleDateString("de-DE") : "";
}

// Full history, loaded from Sendcloud when the timeline is opened
const dialog = ref(false);
const loading = ref(false);
const error = ref("");
const history = ref<any>(null);

async function openTimeline() {
  dialog.value = true;
  loading.value = true;
  error.value = "";
  try {
    const response = await api.get(`/shipping/tracking/${props.invoiceNumber}`);
    history.value = response.data;
  } catch (error_: any) {
    error.value =
      error_.response?.data?.msg || error_.message || "Tracking not available";
  } finally {
    loading.value = false;
  }
}

// Exception details of an event, e.g. "Changed · Receiver"
function eventDetails(event: any) {
  return [readable(event.exception), readable(event.sub_status)]
    .filter(Boolean)
    .join(" · ");
}
</script>

<template>
  <v-tooltip
    v-if="tracking"
    location="top"
    :text="`Since ${formatDateTime(tracking.event_at)}, click for the timeline`"
  >
    <template #activator="{ props: tooltipProps }">
      <v-chip
        v-bind="tooltipProps"
        class="tracking-chip"
        :color="look.color"
        :prepend-icon="look.icon"
        size="small"
        variant="flat"
        @click="openTimeline"
      >
        <span class="text-truncate">{{ tracking.description }}</span>
      </v-chip>
    </template>
  </v-tooltip>

  <v-dialog v-model="dialog" :fullscreen="xs" max-width="560" scrollable>
    <v-card :prepend-icon="look.icon" :title="`Shipment ${invoiceNumber}`">
      <template #subtitle>
        <span v-if="history?.tracking_number">
          {{ history.tracking_number }}
        </span>

        <span v-if="history?.expected_delivery_date">
          · expected {{ formatDate(history.expected_delivery_date) }}
        </span>
      </template>

      <template #append>
        <v-btn icon="mdi-close" variant="text" @click="dialog = false" />
      </template>

      <v-divider />

      <v-card-text>
        <div v-if="loading" class="py-8 text-center">
          <v-progress-circular color="primary" indeterminate />
        </div>

        <v-alert v-else-if="error" type="error" variant="tonal">
          {{ error }}
        </v-alert>

        <div
          v-else-if="!history?.events?.length"
          class="py-8 text-center text-medium-emphasis"
        >
          No tracking events yet
        </div>

        <v-timeline
          v-else
          align="start"
          density="compact"
          side="end"
          truncate-line="both"
        >
          <v-timeline-item
            v-for="(event, index) in history.events"
            :key="`${event.event_at}-${index}`"
            :dot-color="trackingLook(event.phase, event.status_type).color"
            fill-dot
            :icon="trackingLook(event.phase, event.status_type).icon"
            size="small"
          >
            <div
              class="text-body-2"
              :class="{ 'font-weight-bold': index === 0 }"
            >
              {{ event.description }}
            </div>

            <div class="text-caption text-medium-emphasis">
              {{ formatDateTime(event.event_at) }}
              <span v-if="readable(event.phase)">
                · {{ readable(event.phase) }}
              </span>

              <span v-if="event.event_type === 'internal'"> · Sendcloud</span>
            </div>

            <div
              v-if="eventDetails(event)"
              class="text-caption"
              :class="{
                'text-medium-emphasis': !['warning', 'error'].includes(
                  event.status_type,
                ),
              }"
              :style="
                ['warning', 'error'].includes(event.status_type)
                  ? {
                      color: trackingLook(event.phase, event.status_type).color,
                    }
                  : {}
              "
            >
              {{ eventDetails(event) }}
            </div>
          </v-timeline-item>
        </v-timeline>
      </v-card-text>

      <v-divider />

      <v-card-actions>
        <v-spacer />

        <v-btn
          v-if="label?.tracking_url"
          append-icon="mdi-open-in-new"
          color="primary"
          :href="label.tracking_url"
          target="_blank"
          variant="flat"
        >
          Carrier tracking
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.tracking-chip {
  max-width: 100%;
}
</style>
