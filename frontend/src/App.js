import React, { useEffect, useState } from "react";
import axios from "axios";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Link,
  useParams,
  useNavigate,
} from "react-router-dom";

const API_BASE = "http://localhost:8000";

const Table = ({ title, data }) => (
  <div className="w-full md:w-1/2 px-4 mb-8">
    <div className="bg-white rounded-xl shadow-2xl border-2 border-indigo-400 overflow-hidden">
      <h2 className="text-2xl font-bold text-white text-center py-3 bg-gradient-to-r from-indigo-500 to-violet-600 shadow-inner">
        {title}
      </h2>
      <table className="min-w-full divide-y divide-indigo-200">
        <thead className="bg-indigo-100">
          <tr>
            <th className="py-3 px-4 text-left text-indigo-700 text-sm font-semibold uppercase tracking-wider">ФИО</th>
            <th className="py-3 px-4 text-left text-indigo-700 text-sm font-semibold uppercase tracking-wider">Телефон</th>
            <th className="py-3 px-4 text-left text-indigo-700 text-sm font-semibold uppercase tracking-wider">Telegram</th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {data.length === 0 ? (
            <tr>
              <td colSpan={3} className="text-center py-6 text-gray-400 italic">
                Нет данных
              </td>
            </tr>
          ) : (
            data.map((item) => (
              <tr key={item.id} className="hover:bg-indigo-50 transition">
                <td className="py-3 px-4 font-medium text-blue-700">
                  <Link to={`/details/${item.id}`} className="hover:underline">
                    {item.name}
                  </Link>
                </td>
                <td className="py-3 px-4">{item.phone_number}</td>
                <td className="py-3 px-4">@{item.telegram_username}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  </div>
);

function DetailsPage({ onUpdate }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchDetail() {
      setLoading(true);
      try {
        const res = await axios.get(`${API_BASE}/api/volunteerform/${id}`);
        setItem({ ...res.data, source: "volunteerform" });
      } catch {
        try {
          const res = await axios.get(`${API_BASE}/api/waitinglist/${id}`);
          setItem({ ...res.data, source: "waitinglist" });
        } catch {
          try {
            const res = await axios.get(`${API_BASE}/api/mailingpending/${id}`);
            setItem({ ...res.data, source: "mailingpending" });
          } catch {
            setError("Заявка не найдена");
          }
        }
      } finally {
        setLoading(false);
      }
    }
    fetchDetail();
  }, [id]);

  const verifyForm = async () => {
    try {
      await axios.post(`${API_BASE}/api/volunteerform/${id}/verify`);
      alert("Заявка проверена и перенесена в лист ожидания");
      onUpdate?.();
      navigate("/");
    } catch {
      alert("Ошибка при проверке заявки");
    }
  };

  const approveWaiting = async () => {
    try {
      await axios.post(`${API_BASE}/api/waitinglist/${id}/approve`);
      alert("Заявка одобрена и перенесена в рассылку");
      onUpdate?.();
      navigate("/");
    } catch {
      alert("Ошибка при одобрении заявки");
    }
  };

  if (loading) return <p className="p-4 text-center">Загрузка...</p>;
  if (error) return <p className="p-4 text-center text-red-600">{error}</p>;

  return (
    <div className="max-w-xl mx-auto mt-12 p-6 bg-white rounded-lg shadow-lg">
      <h1 className="text-3xl font-bold mb-4 text-center text-gray-800">{item.name}</h1>
      <p className="mb-2"><strong>Телефон:</strong> {item.phone_number}</p>
      <p className="mb-4"><strong>Telegram:</strong> @{item.telegram_username}</p>
      {item.image_url && (
        <img
          src={item.image_url}
          alt="Фото"
          className="w-full rounded-md shadow-md mb-6"
        />
      )}
      {item.source === "volunteerform" && (
        <button
          onClick={verifyForm}
          className="mb-4 w-full px-6 py-2 bg-gradient-to-r from-green-400 to-blue-500 text-white font-semibold rounded-md shadow hover:from-green-500 hover:to-blue-600 transition"
        >
          Проверить
        </button>
      )}
      {item.source === "waitinglist" && (
        <button
          onClick={approveWaiting}
          className="mb-4 w-full px-6 py-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white font-semibold rounded-md shadow hover:from-purple-600 hover:to-indigo-700 transition"
        >
          Одобрить
        </button>
      )}
      <button
        onClick={() => navigate(-1)}
        className="block mx-auto px-6 py-2 bg-gray-300 text-gray-700 font-semibold rounded-md hover:bg-gray-400 transition"
      >
        Назад
      </button>
    </div>
  );
}

export default function App() {
  const [forms, setForms] = useState([]);
  const [waiting, setWaiting] = useState([]);
  const [mailing, setMailing] = useState([]);
  const [reload, setReload] = useState(false);

  const fetchData = async () => {
    try {
      const [formsRes, waitingRes, mailingRes] = await Promise.all([
        axios.get(`${API_BASE}/api/volunteerform`),
        axios.get(`${API_BASE}/api/waitinglist`),
        axios.get(`${API_BASE}/api/mailingpending`),
      ]);
      setForms(formsRes.data);
      setWaiting(waitingRes.data);
      setMailing(mailingRes.data);
    } catch (error) {
      console.error("Ошибка загрузки данных", error);
    }
  };

  useEffect(() => {
    fetchData();
  }, [reload]);

  const approveAllMailing = async () => {
    try {
      await axios.post(`${API_BASE}/mailing/approve-all`);
      alert("Все данные разосланы и регистрация завершена");
      setMailing([]);
      setReload(!reload);
    } catch {
      alert("Ошибка при рассылке");
    }
  };

  return (
    <Router>
      <Routes>
        <Route
          path="/"
          element={
            <div className="min-h-screen bg-gradient-to-b from-indigo-50 to-indigo-100 p-6">
              <div className="flex flex-col md:flex-row gap-6 max-w-7xl mx-auto">
                <Table title="Новые заявки" data={forms} />
                <Table title="Лист ожидания" data={waiting} />
                <Table title="Ожидают рассылку" data={mailing} />
              </div>
              <div className="flex justify-center mt-8">
                <button
                  onClick={approveAllMailing}
                  className="px-8 py-3 bg-gradient-to-r from-green-400 to-blue-500 text-white font-semibold rounded-lg shadow-lg hover:from-green-500 hover:to-blue-600 transition"
                >
                  Разослать и завершить регистрацию
                </button>
              </div>
            </div>
          }
        />
        <Route
          path="/details/:id"
          element={<DetailsPage onUpdate={() => setReload((prev) => !prev)} />}
        />
      </Routes>
    </Router>
  );
}
