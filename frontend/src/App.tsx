import "./App.css";
import { useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

type Cafe = {
  station: string;
  name: string;
  address?: string;
  access?: string;
  open?: string;
  url?: string;
  catch?: string;
  genre?: string;
  budget?: string;
};

type Station = {
  name: string;
  lines: string[];
  lat?: number | null;
  lon?: number | null;
  position: number;
};

type CafesByStation = {
  station: string;
  cafes: Cafe[];
};

type ChatResponse = {
  reply: string;
  route?: Station[];
  cafesByStation?: CafesByStation[];
};

type ChatMessage = {
  speaker: "user" | "bot";
  text: string;
};

function MapPanel({ route }: { route: Station[] }) {
  const plottedRoute = useMemo(() => {
    const withCoords = route.filter((station) => station.lat && station.lon);

    if (withCoords.length >= 2) {
      const lats = withCoords.map((station) => station.lat as number);
      const lons = withCoords.map((station) => station.lon as number);
      const minLat = Math.min(...lats);
      const maxLat = Math.max(...lats);
      const minLon = Math.min(...lons);
      const maxLon = Math.max(...lons);

      return route.map((station) => {
        if (!station.lat || !station.lon) {
          return {
            ...station,
            x: station.position * 88 + 6,
            y: 50,
          };
        }

        return {
          ...station,
          x: ((station.lon - minLon) / Math.max(maxLon - minLon, 0.001)) * 84 + 8,
          y: (1 - (station.lat - minLat) / Math.max(maxLat - minLat, 0.001)) * 72 + 14,
        };
      });
    }

    return route.map((station, index) => ({
      ...station,
      x: station.position * 88 + 6,
      y: index % 2 === 0 ? 42 : 58,
    }));
  }, [route]);

  if (route.length === 0) {
    return (
      <section className="panel map-panel empty-panel">
        <h2>経路</h2>
        <p>出発駅と到着駅が確定すると、ここに京王線・小田急線内の経路を表示します。</p>
      </section>
    );
  }

  const polyline = plottedRoute.map((station) => `${station.x},${station.y}`).join(" ");

  return (
    <section className="panel map-panel">
      <div className="panel-title">
        <h2>経路</h2>
        <span>{route.length}駅</span>
      </div>

      <div className="route-map" aria-label="経路図">
        <svg viewBox="0 0 100 100" role="img">
          <polyline className="route-line" points={polyline} />
          {plottedRoute.map((station, index) => (
            <g key={`${station.name}-${index}`}>
              <circle className={index === 0 || index === plottedRoute.length - 1 ? "station-dot endpoint" : "station-dot"} cx={station.x} cy={station.y} r="2.8" />
              {(index === 0 || index === plottedRoute.length - 1 || route.length <= 10 || index % 3 === 0) && (
                <text x={station.x} y={station.y - 5} textAnchor="middle">
                  {station.name}
                </text>
              )}
            </g>
          ))}
        </svg>
      </div>

      <div className="route-strip">
        {route.map((station, index) => (
          <div className="route-stop" key={`${station.name}-strip-${index}`}>
            <strong>{station.name}</strong>
            <span>{station.lines.join(" / ")}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function CafePanel({ cafesByStation }: { cafesByStation: CafesByStation[] }) {
  const stationsWithCafes = cafesByStation.filter((item) => item.cafes.length > 0);

  return (
    <section className="panel cafes-panel">
      <div className="panel-title">
        <h2>カフェ候補</h2>
        <span>{stationsWithCafes.length}駅</span>
      </div>

      {stationsWithCafes.length === 0 ? (
        <p className="panel-note">経路上の駅からカフェ候補を検索すると、ここに駅別で表示します。</p>
      ) : (
        <div className="cafe-groups">
          {stationsWithCafes.map((group) => (
            <div className="cafe-group" key={group.station}>
              <h3>{group.station}駅周辺</h3>
              <div className="cafe-list">
                {group.cafes.map((cafe) => (
                  <article className="cafe-card" key={`${group.station}-${cafe.name}`}>
                    <div>
                      <h4>{cafe.name}</h4>
                      <p>{cafe.catch || cafe.genre || "カフェ候補"}</p>
                    </div>
                    <dl>
                      {cafe.budget && (
                        <>
                          <dt>予算</dt>
                          <dd>{cafe.budget}</dd>
                        </>
                      )}
                      {cafe.open && (
                        <>
                          <dt>営業時間</dt>
                          <dd>{cafe.open}</dd>
                        </>
                      )}
                      {cafe.access && (
                        <>
                          <dt>アクセス</dt>
                          <dd>{cafe.access}</dd>
                        </>
                      )}
                    </dl>
                    {cafe.url && (
                      <a href={cafe.url} target="_blank" rel="noreferrer">
                        店舗ページ
                      </a>
                    )}
                  </article>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      speaker: "bot",
      text: "こんにちは。京王線・小田急線の経路上で立ち寄りやすいカフェを探します。出発駅、到着駅、利用目的、時刻を教えてください。",
    },
  ]);
  const [input, setInput] = useState("");
  const [route, setRoute] = useState<Station[]>([]);
  const [cafesByStation, setCafesByStation] = useState<CafesByStation[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    if (input.trim() === "" || isLoading) return;

    const userInput = input.trim();

    setMessages((prev) => [...prev, { speaker: "user", text: userInput }]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userInput,
        }),
      });

      const data = (await response.json()) as ChatResponse;

      setMessages((prev) => [...prev, { speaker: "bot", text: data.reply }]);
      setRoute(data.route ?? []);
      setCafesByStation(data.cafesByStation ?? []);
    } catch {
      setMessages((prev) => [
        ...prev,
        { speaker: "bot", text: "バックエンドに接続できませんでした。FastAPIサーバーが起動しているか確認してください。" },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Keio / Odakyu route cafe finder</p>
          <h1>Route Cafe Bot</h1>
        </div>
        <div className="status-pill">WebAPI: 駅情報 + カフェ情報</div>
      </header>

      <div className="workspace">
        <section className="chat-panel">
          <div className="chat-box">
            {messages.map((message, index) => (
              <div key={index} className={`message ${message.speaker}`}>
                <span>{message.speaker === "user" ? "あなた" : "Bot"}</span>
                <p>{message.text}</p>
              </div>
            ))}
            {isLoading && (
              <div className="message bot">
                <span>Bot</span>
                <p>経路とカフェを検索しています...</p>
              </div>
            )}
          </div>

          <div className="input-area">
            <input
              type="text"
              placeholder="例: 新宿から善行まで、作業できるカフェを今日18時に使いたい"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.nativeEvent.isComposing) {
                  handleSend();
                }
              }}
            />

            <button onClick={handleSend} disabled={isLoading}>
              送信
            </button>
          </div>
        </section>

        <aside className="insight-column">
          <MapPanel route={route} />
          <CafePanel cafesByStation={cafesByStation} />
        </aside>
      </div>
    </main>
  );
}

export default App;
