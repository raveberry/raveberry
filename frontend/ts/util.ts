/** Transform the given string from camel case to kebab case
 * @param {string} str the string to be transformed
 * @return {string} the transformed string */
export function kebabize(str) {
  return str.split('').map((letter, idx) => {
    return letter.toUpperCase() === letter ?
        `${idx !== 0 ? '-' : ''}${letter.toLowerCase()}` :
        letter;
  }).join('');
}
