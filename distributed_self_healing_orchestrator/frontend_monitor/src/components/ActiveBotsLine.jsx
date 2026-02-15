import React from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

function ActiveBotsLine({ labels, data }) {
  const chartData = {
    labels: labels,
    datasets: [
      {
        label: 'Active bots',
        data: data,
        borderColor: 'rgba(96,165,250,0.9)',
        backgroundColor: 'rgba(96,165,250,0.12)',
        tension: 0.25,
        fill: true,
      },
    ],
  }

  const options = {
    maintainAspectRatio: false,
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          precision: 0,
        },
      },
    },
  }

  return (
    <div style={{ height: '200px' }}>
      <Line data={chartData} options={options} />
    </div>
  )
}

export default ActiveBotsLine
