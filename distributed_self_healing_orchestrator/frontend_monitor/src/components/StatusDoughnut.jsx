import React from 'react'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'
import { Doughnut } from 'react-chartjs-2'

ChartJS.register(ArcElement, Tooltip, Legend)

function StatusDoughnut({ running, failed }) {
  const data = {
    labels: ['Running', 'Failed'],
    datasets: [
      {
        data: [running, failed],
        backgroundColor: ['rgba(16,185,129,0.9)', 'rgba(239,68,68,0.9)'],
        hoverOffset: 6,
      },
    ],
  }

  const options = {
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
      },
    },
  }

  return (
    <div style={{ height: '200px' }}>
      <Doughnut data={data} options={options} />
    </div>
  )
}

export default StatusDoughnut
