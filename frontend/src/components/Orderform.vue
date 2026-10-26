<template>
  <div class="order-page">
    <!-- Hero with the info as "how it works" steps -->
    <v-sheet class="hero pa-6 pa-md-10 mb-6" rounded="lg">
      <div class="text-overline hero-overline">BSH Board</div>

      <h1 class="text-h4 text-md-h3 font-weight-bold mb-2">
        Order your BSH Board
      </h1>

      <p class="text-body-1 hero-text mb-6">
        This is a side project, not a webshop. This little form helps me process
        orders more conveniently.
      </p>

      <v-row dense>
        <v-col
          v-for="(step, n) in steps"
          :key="step.title"
          cols="12"
          md="3"
          sm="6"
        >
          <div class="step d-flex align-start">
            <v-avatar class="mr-3 flex-shrink-0" color="white" size="40">
              <v-icon color="primary" :icon="step.icon" />
            </v-avatar>

            <div>
              <div class="font-weight-bold">{{ n + 1 }}. {{ step.title }}</div>
              <div class="text-body-2 hero-text">{{ step.text }}</div>
            </div>
          </div>
        </v-col>
      </v-row>
    </v-sheet>

    <v-alert
      v-if="submitted"
      class="mb-6"
      icon="mdi-check-circle"
      prominent
      rounded="lg"
      title="Thank you for your order!"
      type="success"
      variant="tonal"
    >
      I'll check if I have boards available and send you an invoice by email to
      <strong>{{ order.email }}</strong
      >.
    </v-alert>

    <v-form
      v-else
      ref="form"
      v-model="isFormValid"
      @submit.prevent="handleSubmit"
    >
      <!-- Honeypot for bots, hidden from humans -->
      <input
        v-model="website"
        aria-hidden="true"
        autocomplete="off"
        class="honeypot"
        name="website"
        tabindex="-1"
        type="text"
      />

      <v-row>
        <v-col cols="12" lg="8">
          <!-- Items -->
          <v-card border class="mb-6" rounded="lg" variant="flat">
            <v-card-item>
              <template #prepend>
                <v-avatar color="primary" size="32">1</v-avatar>
              </template>

              <v-card-title>Choose your items</v-card-title>
            </v-card-item>

            <v-card-text>
              <v-alert
                v-if="orderStore.productsError"
                class="mb-4"
                density="compact"
                type="error"
                variant="tonal"
              >
                The items could not be loaded, please try again later.
              </v-alert>

              <v-row>
                <v-col v-for="item in items" :key="item.id" cols="12" sm="6">
                  <v-card
                    class="product h-100"
                    :class="{ 'product--selected': item.quantity > 0 }"
                    rounded="lg"
                    variant="outlined"
                  >
                    <v-card-item>
                      <template #prepend>
                        <v-avatar color="primary" rounded="lg" variant="tonal">
                          <v-icon :icon="item.icon" />
                        </v-avatar>
                      </template>

                      <v-card-title class="text-wrap">{{
                        item.name
                      }}</v-card-title>

                      <v-card-subtitle>
                        {{ formatPrice(item.unitPrice) }} each
                      </v-card-subtitle>
                    </v-card-item>

                    <v-card-actions class="px-4 pb-4">
                      <v-number-input
                        v-model="quantities[item.id]"
                        control-variant="split"
                        density="compact"
                        hide-details
                        inset
                        :max="99"
                        :min="0"
                        style="max-width: 160px"
                        variant="outlined"
                      />

                      <v-spacer />

                      <span class="text-h6 font-weight-bold">
                        {{ formatPrice(item.unitPrice * item.quantity) }}
                      </span>
                    </v-card-actions>
                  </v-card>
                </v-col>
              </v-row>

              <v-alert
                class="mt-4"
                density="compact"
                icon="mdi-information-outline"
                type="info"
                variant="tonal"
              >
                You need one 3-pin RAST connector for the board itself, plus a
                3-pin or 4-pin one for your machine. See the
                <a href="#faq">FAQ</a> below.
              </v-alert>
            </v-card-text>
          </v-card>

          <!-- Address -->
          <v-card border rounded="lg" variant="flat">
            <v-card-item>
              <template #prepend>
                <v-avatar color="primary" size="32">2</v-avatar>
              </template>

              <v-card-title>Shipping address</v-card-title>

              <v-card-subtitle>
                Contact person and phone are optional, everything else is
                required
              </v-card-subtitle>
            </v-card-item>

            <v-card-text>
              <v-row dense>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="order.firstname"
                    autocomplete="given-name"
                    label="First name"
                    prepend-inner-icon="mdi-account"
                    :rules="[rules.required]"
                    variant="outlined"
                  />
                </v-col>

                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="order.lastname"
                    autocomplete="family-name"
                    label="Last name"
                    :rules="[rules.required]"
                    variant="outlined"
                  />
                </v-col>

                <v-col cols="12">
                  <v-text-field
                    v-model="order.contact"
                    autocomplete="off"
                    hint="Optional, e.g. a company contact or your forum nickname"
                    label="Contact person (optional)"
                    prepend-inner-icon="mdi-card-account-details"
                    :rules="[rules.maxLength]"
                    variant="outlined"
                  />
                </v-col>

                <v-col cols="12" md="7">
                  <v-text-field
                    v-model="order.email"
                    autocomplete="email"
                    label="Email address"
                    prepend-inner-icon="mdi-email"
                    :rules="[rules.required, rules.email]"
                    type="email"
                    variant="outlined"
                  />
                </v-col>

                <v-col cols="12" md="5">
                  <v-text-field
                    v-model="order.phone"
                    autocomplete="tel"
                    hint="Optional, helps the carrier to reach you"
                    label="Phone (optional)"
                    prepend-inner-icon="mdi-phone"
                    :rules="[rules.phone]"
                    type="tel"
                    variant="outlined"
                  />
                </v-col>

                <v-col cols="12">
                  <v-text-field
                    v-model="order.address"
                    autocomplete="street-address"
                    label="Street and house number"
                    prepend-inner-icon="mdi-home"
                    :rules="[rules.required]"
                    variant="outlined"
                  />
                </v-col>

                <v-col cols="12" md="4">
                  <v-text-field
                    v-model="order.postalcode"
                    autocomplete="postal-code"
                    label="Postal code"
                    :rules="[rules.required]"
                    variant="outlined"
                  />
                </v-col>

                <v-col cols="12" md="8">
                  <v-text-field
                    v-model="order.city"
                    autocomplete="address-level2"
                    label="City"
                    :rules="[rules.required]"
                    variant="outlined"
                  />
                </v-col>

                <v-col cols="12">
                  <v-autocomplete
                    v-model="order.country"
                    autocomplete="country"
                    clearable
                    item-title="name"
                    item-value="code"
                    :items="COUNTRIES"
                    label="Country"
                    prepend-inner-icon="mdi-earth"
                    :rules="[rules.required]"
                    variant="outlined"
                  >
                    <template #item="{ props, item }">
                      <v-list-item v-bind="props" :title="item.name">
                        <template #prepend>
                          <span
                            class="text-h6 mr-2"
                            :class="`fi fi-${item.code.toLowerCase()}`"
                            style="border-radius: 2px"
                          />
                        </template>
                      </v-list-item>
                    </template>

                    <template #selection="{ item }">
                      <span
                        class="text-h6 mr-2"
                        :class="`fi fi-${order.country.toLowerCase()}`"
                        style="border-radius: 2px"
                      />

                      <span>{{ item.name }}</span>
                    </template>
                  </v-autocomplete>
                </v-col>

                <v-col v-if="regions.length > 0" cols="12">
                  <v-autocomplete
                    v-model="order.region"
                    autocomplete="address-level1"
                    hint="Required by the carrier for this country"
                    item-title="name"
                    item-value="code"
                    :items="regions"
                    label="State / Province"
                    persistent-hint
                    prepend-inner-icon="mdi-map-marker"
                    :rules="[rules.required]"
                    variant="outlined"
                  >
                    <template #item="{ props, item }">
                      <v-list-item v-bind="props" :subtitle="item.code" />
                    </template>
                  </v-autocomplete>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Summary, sticks while scrolling on large screens -->
        <v-col cols="12" lg="4">
          <v-card class="summary" elevation="4" rounded="lg">
            <v-card-item>
              <template #prepend>
                <v-icon color="primary" icon="mdi-cart" />
              </template>

              <v-card-title>Your order</v-card-title>
            </v-card-item>

            <v-divider />

            <v-card-text>
              <div
                v-if="selectedItems.length === 0"
                class="text-medium-emphasis text-center py-6"
              >
                <v-icon class="mb-2" icon="mdi-cart-outline" size="40" />
                <div>Nothing selected yet</div>
              </div>

              <div
                v-for="item in selectedItems"
                :key="item.id"
                class="d-flex justify-space-between py-1"
              >
                <span>{{ item.quantity }} × {{ item.name }}</span>

                <span class="amount">
                  {{ formatPrice(item.unitPrice * item.quantity) }}
                </span>
              </div>
            </v-card-text>

            <v-divider />

            <v-card-text>
              <div class="d-flex justify-space-between py-1">
                <span>Items</span>
                <span class="amount">{{ formatPrice(subtotal) }}</span>
              </div>

              <div class="d-flex justify-space-between py-1">
                <span>
                  Shipping
                  <span v-if="shipping" class="text-medium-emphasis">
                    ({{ shipping.name }})
                  </span>
                </span>

                <v-progress-circular
                  v-if="shippingLoading"
                  indeterminate
                  size="16"
                  width="2"
                />

                <span v-else-if="shipping" class="amount">
                  {{ formatPrice(shipping.price) }}
                </span>

                <span v-else class="text-medium-emphasis">
                  {{ order.country ? "not available" : "select country" }}
                </span>
              </div>
            </v-card-text>

            <v-divider />

            <v-card-text
              class="d-flex justify-space-between align-center text-h6"
            >
              <span>Total</span>

              <span class="amount font-weight-bold">
                {{ formatPrice(total) }}
              </span>
            </v-card-text>

            <v-card-actions class="px-4 pb-4 flex-column align-stretch">
              <v-alert
                v-if="submitError"
                class="mb-3"
                density="compact"
                type="error"
                variant="tonal"
              >
                {{ submitError }}
              </v-alert>

              <v-btn
                block
                color="primary"
                :disabled="selectedItems.length === 0 || !shipping"
                :loading="submitting"
                prepend-icon="mdi-send"
                size="large"
                type="submit"
                variant="flat"
              >
                Submit order
              </v-btn>

              <div class="text-caption text-medium-emphasis text-center mt-3">
                No payment now, you'll receive an invoice by email.
              </div>
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>
    </v-form>

    <!-- FAQ -->
    <section id="faq" class="mt-10">
      <h2 class="text-h5 font-weight-bold mb-4">
        <v-icon class="mr-2" color="primary" icon="mdi-help-circle" />
        Frequently asked questions
      </h2>

      <v-expansion-panels variant="accordion">
        <v-expansion-panel
          v-for="faq in faqs"
          :key="faq.question"
          :text="faq.answer"
          :title="faq.question"
        />
      </v-expansion-panels>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { COUNTRIES } from "@/constants/countries";
import { type Region, type Shipping, useOrderStore } from "@/store/order";

const orderStore = useOrderStore();

const form = ref(null);
const isFormValid = ref(false);
const submitting = ref(false);
const submitError = ref<string | null>(null);
const submitted = ref(false);

const steps = [
  {
    icon: "mdi-cart-check",
    title: "Order",
    text: "Pick your items and send this form.",
  },
  {
    icon: "mdi-file-document-outline",
    title: "Invoice",
    text: "I'll send you an invoice by email, but only if boards are available.",
  },
  {
    icon: "mdi-cash-check",
    title: "Payment",
    text: "Pay the invoice by bank transfer or PayPal.",
  },
  {
    icon: "mdi-truck-fast",
    title: "Shipping",
    text: "Once paid, I usually ship the next business day.",
  },
];

const faqs = [
  {
    question: "What connector type do I need?",
    answer:
      "You need one 3-pin RAST connector for the board itself. You will also need a 3-pin or a 4-pin RAST connector for the machine side. Which one depends on your model, but there is a definitive list which model needs which connector.",
  },
  {
    question: "Can you sell me ready to use RAST connection cables?",
    answer:
      "Unfortunately, no. Not at this point, maybe I can in the future but there are no plans for this now. For me 3x0.34mm² (22 AWG) cable worked out pretty well. Alternatively you can use single wires of this size.",
  },
  {
    question: "Do I get a tracking number?",
    answer: "Yes, you'll get a shipping number via email.",
  },
];

const order = ref({
  firstname: "",
  lastname: "",
  contact: "",
  email: "",
  phone: "",
  address: "",
  city: "",
  postalcode: "",
  country: "",
  region: "",
});
const website = ref("");

// Items and prices come from Invio
const quantities = ref<Record<string, number>>({});

function iconFor(name: string) {
  const n = name.toLowerCase();
  if (n.includes("case")) return "mdi-package-variant-closed";
  if (n.includes("stecker") || n.includes("connector")) return "mdi-connection";
  return "mdi-chip";
}

const items = computed(() =>
  orderStore.products
    .filter((p) => p.category === "goods")
    .map((p) => ({
      ...p,
      icon: iconFor(p.name),
      quantity: quantities.value[p.id] ?? 0,
    })),
);

const selectedItems = computed(() =>
  items.value.filter((item) => item.quantity > 0),
);

const subtotal = computed(() =>
  selectedItems.value.reduce(
    (sum, item) => sum + item.unitPrice * item.quantity,
    0,
  ),
);

// Start every product at 0 so the -/+ buttons work right away
watch(
  () => orderStore.products,
  (products) => {
    for (const p of products) {
      quantities.value[p.id] ??= 0;
    }
  },
  { immediate: true },
);

// Shipping costs depend on the destination country
const shipping = ref<Shipping | null>(null);
const shippingLoading = ref(false);

// State/province list for countries whose carriers need it
const regions = ref<Region[]>([]);

watch(
  () => order.value.country,
  async (country) => {
    order.value.region = "";
    regions.value = country ? await orderStore.fetchRegions(country) : [];
  },
);

watch(
  () => order.value.country,
  async (country) => {
    shipping.value = null;
    if (!country) return;
    shippingLoading.value = true;
    shipping.value = await orderStore.fetchShipping(country);
    shippingLoading.value = false;
  },
);

const total = computed(() => subtotal.value + (shipping.value?.price ?? 0));

function formatPrice(value: number) {
  return `${value.toFixed(2)} €`;
}

// Validation rules array of functions returning true or an error message string
const rules = {
  required: (val: unknown) => !!val || "This field is required.",
  email: (val: string) =>
    /.[^\n\r@\u2028\u2029]*@.+\..+/.test(val) ||
    "Must be a valid email address.",
  minQuantity: (val: number) => val >= 1 || "Quantity must be at least 1.",
  maxLength: (val: string) => !val || val.length <= 200 || "Too long.",
  phone: (val: string) =>
    !val ||
    /^\+?[0-9 ()/-]{4,30}$/.test(val.trim()) ||
    "Must be a valid phone number.",
};

type FormInstance = {
  validate: () => Promise<{ valid: boolean }>;
};

async function handleSubmit() {
  const formRef = form.value as FormInstance | null;
  const { valid } = (await formRef?.validate()) ?? { valid: false };

  if (!valid) return;

  submitting.value = true;
  submitError.value = null;
  submitError.value = await orderStore.submitOrder({
    ...order.value,
    website: website.value,
    items: selectedItems.value.map((item) => ({
      productId: item.id,
      quantity: item.quantity,
    })),
  });
  submitting.value = false;
  if (!submitError.value) {
    submitted.value = true;
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
}

onMounted(() => {
  orderStore.fetchProducts();
});
</script>

<style scoped>
.order-page {
  max-width: 1280px;
  margin: 0 auto;
}

.hero {
  background: linear-gradient(
    135deg,
    rgb(var(--v-theme-primary)) 0%,
    rgb(var(--v-theme-secondary)) 100%
  );
  color: #fff;
}

.hero-overline {
  opacity: 0.85;
  letter-spacing: 0.2em;
}

.hero-text {
  opacity: 0.9;
}

.product {
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.product--selected {
  border-color: rgb(var(--v-theme-primary));
  box-shadow: 0 0 0 1px rgb(var(--v-theme-primary));
}

.honeypot {
  position: absolute;
  left: -10000px;
  width: 1px;
  height: 1px;
  overflow: hidden;
}

.amount {
  font-variant-numeric: tabular-nums;
}

@media (min-width: 1280px) {
  .summary {
    position: sticky;
    top: 88px;
  }
}
</style>
