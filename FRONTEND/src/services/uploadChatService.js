import api from './api';

export const uploadDocument = async (token, file) => {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await api.post(
      '/upload-chat/upload',
      formData,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  } catch (error) {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error("Failed to upload document. Please try again.");
  }
};

export const queryDocument = async (token, documentId, question, conversationId = null, signal = null) => {
  try {
    const payload = {
      document_id: documentId,
      question: question
    };
    
    if (conversationId) {
      payload.conversation_id = conversationId;
    }
    
    const response = await api.post(
      '/upload-chat/query',
      payload,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        signal
      }
    );
    return response.data;
  } catch (error) {
    if (error.name === 'CanceledError' || error.message === 'canceled') {
      throw error;
    }
    if (error.response?.status === 429) {
      throw new Error("You are asking questions too quickly. Please wait a moment.");
    }
    if (error.response?.data?.detail) {
        throw new Error(error.response.data.detail);
    }
    throw new Error("Failed to query document. Please try again.");
  }
};
