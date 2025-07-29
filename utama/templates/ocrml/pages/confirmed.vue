<template>
  <div class="page-container">
    <h2>Data OCR yang Telah Dikonfirmasi</h2>

    <div class="status-tabs">
      <button :class="{ active: status === 'true' }" @click="loadConfirmed('true')">✅ Benar</button>
      <button :class="{ active: status === 'false' }" @click="loadConfirmed('false')">❌ Salah</button>
    </div>

    <div v-if="loading" class="loading-indicator">
      <div class="spinner"></div>
      <p>Memuat data...</p>
    </div>

    <div v-if="errorMessage" class="error-message">{{ errorMessage }}</div>
    <div v-if="confirmedReceipts.length === 0 && !loading">Tidak ada data.</div>

    <div v-if="confirmedReceipts.length > 0" class="receipt-card">
      <h3>Struk #{{ currentReceipt.receipt_id }}</h3>
      <p><strong>Invoice:</strong> {{ currentReceipt.receipt_data.invoice_number }}</p>
      <p><strong>Tanggal:</strong> {{ currentReceipt.receipt_data.tanggal }}</p>
      <p><strong>Toko:</strong> {{ currentReceipt.receipt_data.nama_toko }}</p>
      <p><strong>Total Belanja:</strong> {{ formatCurrency(currentReceipt.receipt_data.total_belanja) }}</p>

      <h4>Barang</h4>
      <ul>
        <li v-for="(item, i) in currentReceipt.matched_data" :key="i" class="item-card">
          <p><strong>OCR Nama:</strong> {{ item.ocr_result.name }}</p>
          <p><strong>Matched:</strong> {{ item.name || 'Tidak ditemukan' }}</p>
        </li>
      </ul>
      <p><strong>Feedback:</strong> {{ currentReceipt.feedback || '-' }}</p>

      <div class="navigation-buttons" v-if="confirmedReceipts.length > 1">
        <button @click="showPrev" :disabled="currentIndex === 0">Sebelumnya</button>
        <span>Struk {{ currentIndex + 1 }} dari {{ confirmedReceipts.length }}</span>
        <button @click="showNext" :disabled="currentIndex === confirmedReceipts.length - 1">Berikutnya</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'

const confirmedReceipts = ref([])
const loading = ref(false)
const errorMessage = ref('')
const status = ref('true')
const currentIndex = ref(0)

const currentReceipt = computed(() => confirmedReceipts.value[currentIndex.value])

const loadConfirmed = async (val) => {
  status.value = val
  loading.value = true
  errorMessage.value = ''
  try {
    const res = await fetch(`http://localhost:8000/ocr/confirmed?status=${val}`)
    if (!res.ok) throw new Error('Gagal memuat data konfirmasi')
    confirmedReceipts.value = await res.json()
    currentIndex.value = 0 // reset halaman
  } catch (err) {
    errorMessage.value = 'Terjadi kesalahan: ' + err.message
  } finally {
    loading.value = false
  }
}

const formatCurrency = (amount) => {
  if (typeof amount !== 'number' || isNaN(amount)) return 'N/A'
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR'
  }).format(amount)
}

const showPrev = () => {
  if (currentIndex.value > 0) currentIndex.value--
}

const showNext = () => {
  if (currentIndex.value < confirmedReceipts.value.length - 1) currentIndex.value++
}

onMounted(() => loadConfirmed(status.value))
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.status-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.status-tabs button {
  padding: 8px 16px;
  border: 1px solid #ddd;
  background: #f5f5f5;
  cursor: pointer;
  border-radius: 5px;
}

.status-tabs button.active {
  background: #3498db;
  color: white;
  font-weight: bold;
}

.receipt-card {
  background: #f9f9f9;
  padding: 20px;
  margin-bottom: 25px;
  border-radius: 10px;
  border: 1px solid #ccc;
}

.item-card {
  background: #eef5f7;
  border-left: 4px solid #3498db;
  padding: 10px;
  margin-bottom: 10px;
  border-radius: 5px;
}

.loading-indicator {
  text-align: center;
}

.spinner {
  width: 30px;
  height: 30px;
  border: 4px solid #ccc;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  margin: auto;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-message {
  background: #ffe5e5;
  color: #cc0000;
  padding: 10px;
  border-radius: 5px;
  margin-bottom: 15px;
}

.navigation-buttons {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
}
</style>
