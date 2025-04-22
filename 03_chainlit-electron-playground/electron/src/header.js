document.addEventListener('DOMContentLoaded', () => {
    const returnButton = document.getElementById('returnButton');
    returnButton.addEventListener('click', async () => {
      await window.api.returnToSettings();
    });
  });