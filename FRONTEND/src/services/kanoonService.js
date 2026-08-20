import api from './api';

export const askKanoon = async (token, question, conversationId = null) => {
  try {
    const payload = { question };
    if (conversationId) {
      payload.conversation_id = conversationId;
    }
    
    const response = await api.post(
      '/kanoon/query',
      payload,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    return response.data;
  } catch (error) {
    if (error.response?.status === 429) {
      throw new Error("You are asking questions too quickly. Please wait a moment.");
    }
    if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
    }
    throw new Error("Failed to connect to Know Your Kanoon. Please try again.");
  }
};
