import { useState } from "react";

function App() {
  const [messages, setMessages] = useState([
    "🤖 こんにちは！出発駅と到着駅を教えてください。",
  ]);

  const [input, setInput] = useState("");

  const handleSend = () => {
    if (input.trim() === "") return;

    setMessages([...messages, `👤 ${input}`]);
    setInput("");
  };

  return (
    <div
      style={{
        maxWidth: "800px",
        margin: "0 auto",
        padding: "20px",
      }}
    >
      <h1>Route Cafe Bot</h1>

      <div
        style={{
          border: "1px solid #ddd",
          borderRadius: "8px",
          padding: "16px",
          minHeight: "400px",
          marginBottom: "16px",
        }}
      >
        {messages.map((message, index) => (
          <p key={index}>{message}</p>
        ))}
      </div>

      <div>
        <input
          type="text"
          placeholder="メッセージを入力"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          style={{
            width: "80%",
            padding: "8px",
          }}
        />

        <button
          onClick={handleSend}
          style={{
            marginLeft: "8px",
            padding: "8px 16px",
          }}
        >
          送信
        </button>
      </div>
    </div>
  );
}

export default App;