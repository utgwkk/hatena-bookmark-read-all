document.querySelectorAll('.read-button').forEach(elem => {
  elem.onclick = () => {
    const buttonLine = elem.parentElement.parentElement;
    const aTag = buttonLine.children[0].children[0];
    const href = aTag.getAttribute('href');
    // TODO: queryじゃなくてbodyに含める
    fetch(`/mark_as_read?url=${encodeURI(href)}`, {
      method: 'POST'
    })
    .then(resp => {
      console.log(resp);
      buttonLine.remove();
    })
    .catch(err => console.error(err));
  };
});

document.querySelector('.read-all-button').onclick = () => {
  if (window.confirm('本当に全部読んだことにしていいですか？')){
    document.querySelectorAll('.read-button').forEach((elem, idx) => {
      const waitSeconds = 1000 * idx;
      window.setTimeout(() => elem.click(), waitSeconds);
    });
  }
};
