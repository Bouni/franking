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

    <v-form ref="form" v-model="isFormValid" @submit.prevent="handleSubmit">
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
              <v-row>
                <v-col
                  v-for="item in order.items"
                  :key="item.article_number"
                  cols="12"
                  sm="6"
                >
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
                        {{ formatPrice(item.price) }} each
                      </v-card-subtitle>
                    </v-card-item>

                    <v-card-actions class="px-4 pb-4">
                      <v-number-input
                        v-model="item.quantity"
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
                        {{ formatPrice(item.price * item.quantity) }}
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

              <v-card-subtitle>All fields are required</v-card-subtitle>
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
                    v-model="order.email"
                    autocomplete="email"
                    label="Email address"
                    prepend-inner-icon="mdi-email"
                    :rules="[rules.required, rules.email]"
                    type="email"
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
                :key="item.article_number"
                class="d-flex justify-space-between py-1"
              >
                <span>{{ item.quantity }} × {{ item.name }}</span>

                <span class="amount">
                  {{ formatPrice(item.price * item.quantity) }}
                </span>
              </div>
            </v-card-text>

            <v-divider />

            <v-card-text
              class="d-flex justify-space-between align-center text-h6"
            >
              <span>Sum</span>

              <span class="amount font-weight-bold">
                {{ formatPrice(subtotal) }}
              </span>
            </v-card-text>

            <v-card-actions class="px-4 pb-4 flex-column align-stretch">
              <v-btn
                block
                color="primary"
                :disabled="selectedItems.length === 0"
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
import { computed, onMounted, ref } from "vue";
import { COUNTRIES } from "@/constants/countries";
import { useOrderStore } from "@/store/order";

const orderStore = useOrderStore();

const form = ref(null);
const isFormValid = ref(false);

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
      "Unfortunately, no. Not at this point, maybe I can in the future but there are no plans for this now. For me 3x0.34mm² cable worked out pretty well. Alternatively you can use single wires of this size.",
  },
];

const order = ref({
  firstname: "",
  lastname: "",
  email: "",
  address: "",
  city: "",
  postalcode: "",
  country: "",
  items: [
    {
      name: "BSH Board",
      article_number: "1",
      price: 15,
      quantity: 0,
      icon: "mdi-chip",
    },
    {
      name: "RAST Connector 3-pin",
      article_number: "2",
      price: 1,
      quantity: 0,
      icon: "mdi-connection",
    },
    {
      name: "RAST Connector 4-pin",
      article_number: "3",
      price: 1,
      quantity: 0,
      icon: "mdi-connection",
    },
    {
      name: "BSH Board Case",
      article_number: "4",
      price: 10,
      quantity: 0,
      icon: "mdi-package-variant-closed",
    },
  ],
});

const selectedItems = computed(() =>
  order.value.items.filter((item) => item.quantity > 0),
);

// Calculate subtotal for items only
const subtotal = computed(() => {
  return order.value.items.reduce((sum, item) => {
    return sum + item.price * item.quantity;
  }, 0);
});

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
};

type FormInstance = {
  validate: () => Promise<{ valid: boolean }>;
};

async function handleSubmit() {
  const formRef = form.value as FormInstance | null;
  const { valid } = (await formRef?.validate()) ?? { valid: false };

  if (!valid) return;

  console.log("Order submitted successfully:", order);
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
