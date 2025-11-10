import { useEffect, useRef, memo, useState } from 'react'
import mermaid from 'mermaid'

function MermaidDiagram({ chart }) {
    const containerRef = useRef(null)
    const lastChartRef = useRef('')
    const [isLoading, setIsLoading] = useState(false)

    useEffect(() => {
        mermaid.initialize({
            startOnLoad: false,
            theme: 'base',
            securityLevel: 'loose',
            themeVariables: {
                fontSize: '14px',
                fontFamily: 'var(--font-sans)',
                primaryColor: '#f5f5f5',
                primaryTextColor: '#111',
                primaryBorderColor: '#111',
                lineColor: '#111',
                secondaryColor: '#e5e5e5',
                tertiaryColor: '#f9f9f9',
                clusterBkg: '#f5f5f5',
                clusterBorder: '#111',
                edgeLabelBackground: '#fff',
                nodeTextColor: '#111',
            },
            flowchart: {
                useMaxWidth: false,
                htmlLabels: false,
                curve: 'basis',
            },
        })

        const renderChart = async () => {
            if (!chart || chart === lastChartRef.current) return

            // Clear container first
            if (containerRef.current) {
                containerRef.current.innerHTML = ''
            }

            lastChartRef.current = chart
            let svgId = null

            const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

            setIsLoading(true)

            try {
                // Generate unique ID for each render
                svgId = `mermaid-${Date.now()}-${Math.random().toString(36).slice(2)}`

                const { svg } = await mermaid.render(svgId, chart)

                // await sleep(120_000);

                // Only update if container still exists
                if (containerRef.current) {
                    containerRef.current.innerHTML = svg
                }

            } catch (err) {
                console.error('Mermaid rendering error:', err)
                if (containerRef.current) {
                    containerRef.current.innerHTML = `<div class="text-red-500 text-sm">Failed to render diagram</div>`
                }
            } finally {
                setIsLoading(false)

                // Clean up orphaned divs
                if (svgId){
                    console.log('Mermaid cleaning ID:', svgId)
                    const tempDiv = document.getElementById(`d${svgId}`)
                    if (tempDiv && tempDiv.parentNode) {
                        tempDiv.parentNode.removeChild(tempDiv)
                    }
                } else {
                    console.error('Mermaid no svg ID to clean')
                }
                // const orphans = document.querySelectorAll('div[id^="dmermaid-"]');
                // orphans.forEach(div => div.remove());
                // Clean up the specific temporary div created by mermaid
            }
        }

        renderChart()
    }, [chart])

    return (
        <div className="mermaid-container">
            <div className="mermaid-scroll">
                {isLoading && (
                    <div className="loading-wrapper">
                        {/* <div className="loading-spinner" /> */}
                        <span className="loading-text">Rendering Mermaid Diagram...</span>
                    </div>
                )}
            
                <div ref={containerRef} className="mermaid-svg" />
            </div>
        </div>
    )
}

export default memo(MermaidDiagram)
